import base64
import datetime
import hashlib
import hmac
import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"
SURVEY_FILES = {
    "student": DATA_DIR / "survey_student.json",
    "professor": DATA_DIR / "survey_professor.json",
}
ADMIN_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
}
JWT_SECRET = os.environ.get("ASK_ALMA_JWT_SECRET", "ask-alma-dev-secret").encode("utf-8")
JWT_LIFETIME_SECONDS = 60 * 60 * 8


def base64url_encode(raw):
    """Kodiert Bytes im kompakten JWT-Base64url-Format."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def base64url_decode(value):
    """Dekodiert JWT-Base64url-Werte mit optionaler Auffuellung."""
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def erstelle_jwt(username, role):
    """Erstellt ein signiertes HS256-JWT fuer die lokale Admin-Anmeldung."""
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + JWT_LIFETIME_SECONDS,
    }
    header_segment = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("ascii")
    signature = hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{base64url_encode(signature)}"


def pruefe_jwt(token):
    """Prueft Signatur und Ablaufzeit eines JWT und liefert den Payload."""
    parts = token.split(".")
    if len(parts) != 3:
        return None

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    expected_signature = hmac.new(JWT_SECRET, signing_input, hashlib.sha256).digest()
    try:
        given_signature = base64url_decode(parts[2])
    except (ValueError, TypeError):
        return None

    if not hmac.compare_digest(expected_signature, given_signature):
        return None

    try:
        payload = json.loads(base64url_decode(parts[1]).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None

    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    if payload.get("exp", 0) < now:
        return None

    return payload


def normalisiere_rolle(rolle):
    """Normalisiert Rollenparameter auf bekannte Umfrage-Dateien."""
    rolle = (rolle or "student").strip().lower()
    if rolle not in SURVEY_FILES:
        return None
    return rolle


def lade_umfrage(rolle="student"):
    """Laedt die rollenbasierte Umfragekonfiguration aus der Backend-Datenablage."""
    rolle = normalisiere_rolle(rolle)
    if rolle is None:
        raise ValueError("Unbekannte Rolle.")

    with SURVEY_FILES[rolle].open("r", encoding="utf-8") as file:
        return json.load(file)


def speichere_umfrage(rolle, umfrage):
    """Speichert eine rollenbasierte Umfragekonfiguration formatiert als JSON."""
    with SURVEY_FILES[rolle].open("w", encoding="utf-8") as file:
        json.dump(umfrage, file, ensure_ascii=False, indent=2)
        file.write("\n")


def finde_umfrage_nach_id(survey_id):
    """Sucht die passende Umfrage anhand der survey_id in allen Rollendateien."""
    for rolle in SURVEY_FILES:
        umfrage = lade_umfrage(rolle)
        if umfrage.get("survey_id") == survey_id:
            return rolle, umfrage
    return None, None


def schreibe_ergebnis(payload):
    """Speichert eine einzelne Umfrageantwort als eigene JSON-Datei."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    result_id = str(uuid.uuid4())
    zielpfad = RESULTS_DIR / f"{result_id}.json"

    datensatz = {
        "result_id": result_id,
        "received_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "survey_id": payload["survey_id"],
        "client_timestamp": payload.get("timestamp"),
        "answers": payload["answers"],
    }

    with zielpfad.open("w", encoding="utf-8") as file:
        json.dump(datensatz, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return result_id


def lade_ergebnisse():
    """Laedt Ergebnisdateien und nutzt pandas fuer die tabellarische Aufbereitung."""
    datensaetze = []
    for pfad in sorted(RESULTS_DIR.glob("*.json")):
        with pfad.open("r", encoding="utf-8") as file:
            datensaetze.append(json.load(file))

    if not datensaetze:
        return []

    frame = pd.DataFrame(datensaetze)
    frame = frame.where(pd.notna(frame), None)
    return frame.to_dict(orient="records")


def ist_leer(wert):
    """Bewertet leere Pflichtantworten einheitlich."""
    if wert is None:
        return True
    if isinstance(wert, str):
        return not wert.strip()
    return False


def ist_iso_zeitstempel(wert):
    """Prueft, ob ein Zeitstempel als ISO-8601-Zeichenkette lesbar ist."""
    if not isinstance(wert, str):
        return False

    try:
        datetime.datetime.fromisoformat(wert.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validiere_ergebnis_payload(payload):
    """Prueft Struktur und Antworten fuer eingehende Umfrageantworten."""
    if not isinstance(payload, dict):
        return "Der Anfrage-Inhalt muss ein JSON-Objekt sein."

    if not isinstance(payload.get("survey_id"), str) or not payload["survey_id"].strip():
        return "Das Feld 'survey_id' muss als nicht-leerer Text uebergeben werden."

    if "timestamp" in payload and not ist_iso_zeitstempel(payload["timestamp"]):
        return "Das Feld 'timestamp' muss als ISO-8601-Zeichenkette uebergeben werden."

    if not isinstance(payload.get("answers"), dict):
        return "Das Feld 'answers' muss als Objekt mit Frage-IDs und Antworten uebergeben werden."

    _, umfrage = finde_umfrage_nach_id(payload["survey_id"])
    if umfrage is None:
        return "Die uebergebene 'survey_id' ist fuer diese Backend-Konfiguration unbekannt."

    fragen = {frage["id"]: frage for frage in umfrage.get("questions", [])}
    unbekannte_fragen = sorted(set(payload["answers"].keys()) - set(fragen.keys()))
    if unbekannte_fragen:
        return f"Unbekannte Frage-IDs: {', '.join(unbekannte_fragen)}."

    fehlende_pflichtfragen = [
        frage_id
        for frage_id, frage in fragen.items()
        if frage.get("required") and ist_leer(payload["answers"].get(frage_id))
    ]
    if fehlende_pflichtfragen:
        return f"Pflichtfragen ohne Antwort: {', '.join(fehlende_pflichtfragen)}."

    for frage_id, antwort in payload["answers"].items():
        frage = fragen[frage_id]
        frage_typ = frage.get("type")

        if frage_typ == "multiple_choice":
            erlaubte_werte = {option["value"] for option in frage.get("options", [])}
            if antwort not in erlaubte_werte:
                return f"Antwort fuer '{frage_id}' ist keine erlaubte Option."
        elif frage_typ == "text" and not isinstance(antwort, str):
            return f"Antwort fuer '{frage_id}' muss eine Zeichenkette sein."
        elif frage_typ == "likert":
            if "options" in frage:
                erlaubte_werte = {option["value"] for option in frage.get("options", [])}
                if antwort not in erlaubte_werte:
                    return f"Antwort fuer '{frage_id}' ist kein erlaubter Likert-Wert."
            elif not isinstance(antwort, int) or not 1 <= antwort <= 5:
                return f"Antwort fuer '{frage_id}' muss ein Likert-Wert von 1 bis 5 sein."

    return None


def validiere_frage(frage, umfrage):
    """Prueft neue Fragen vor dem Speichern in der Umfragekonfiguration."""
    if not isinstance(frage, dict):
        return "Der Anfrage-Inhalt muss ein Frage-Objekt sein."

    frage_id = frage.get("id")
    frage_typ = frage.get("type")
    label = frage.get("label")
    erlaubte_typen = {"text", "multiple_choice", "likert"}

    if not isinstance(frage_id, str) or not frage_id.strip():
        return "Das Feld 'id' muss ein nicht-leerer Text sein."
    if any(bestehend.get("id") == frage_id for bestehend in umfrage.get("questions", [])):
        return "Eine Frage mit dieser ID existiert bereits."
    if frage_typ not in erlaubte_typen:
        return "Das Feld 'type' muss text, multiple_choice oder likert sein."
    if not isinstance(label, str) or not label.strip():
        return "Das Feld 'label' muss ein nicht-leerer Text sein."
    if "required" in frage and not isinstance(frage["required"], bool):
        return "Das Feld 'required' muss ein Boolean sein."

    if frage_typ == "multiple_choice":
        options = frage.get("options")
        if not isinstance(options, list) or not options:
            return "Multiple-Choice-Fragen benoetigen eine nicht-leere options-Liste."
        for option in options:
            if not isinstance(option, dict):
                return "Jede Option muss ein Objekt sein."
            if not isinstance(option.get("value"), str) or not option["value"].strip():
                return "Jede Option benoetigt einen nicht-leeren value."
            if not isinstance(option.get("text"), str) or not option["text"].strip():
                return "Jede Option benoetigt einen nicht-leeren text."

    frage.setdefault("required", True)
    return None


class ApiHandler(BaseHTTPRequestHandler):
    """HTTP-Handler fuer die JSON-Schnittstellen des Backends."""

    def _sende_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _lese_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return None

        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _rolle_aus_query(self, parsed_url):
        query = parse_qs(parsed_url.query)
        return normalisiere_rolle(query.get("role", ["student"])[0])

    def _autorisierter_admin(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self._sende_json(401, {"status": "error", "message": "Authorization-Token fehlt."})
            return False

        payload = pruefe_jwt(auth_header.removeprefix("Bearer ").strip())
        if payload is None:
            self._sende_json(401, {"status": "error", "message": "Authorization-Token ist ungueltig."})
            return False

        if payload.get("role") != "admin":
            self._sende_json(403, {"status": "error", "message": "Admin-Rolle erforderlich."})
            return False

        return True

    def do_GET(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path

        if pfad == "/api/health":
            self._sende_json(200, {"status": "ok", "service": "ask-alma-backend"})
            return

        if pfad == "/api/survey":
            rolle = self._rolle_aus_query(parsed_url)
            if rolle is None:
                self._sende_json(400, {"status": "error", "message": "Unbekannte Rolle."})
                return
            self._sende_json(200, lade_umfrage(rolle))
            return

        if pfad == "/api/results":
            if not self._autorisierter_admin():
                return
            self._sende_json(200, lade_ergebnisse())
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_POST(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path

        if pfad == "/api/login":
            payload = self._lese_json_body()
            username = payload.get("username") if isinstance(payload, dict) else None
            password = payload.get("password") if isinstance(payload, dict) else None
            user = ADMIN_USERS.get(username)

            if user is None or user["password"] != password:
                self._sende_json(401, {"status": "error", "message": "Login fehlgeschlagen."})
                return

            token = erstelle_jwt(username, user["role"])
            self._sende_json(200, {"token": token, "role": user["role"]})
            return

        if pfad == "/api/results":
            payload = self._lese_json_body()
            fehler = validiere_ergebnis_payload(payload)
            if fehler:
                self._sende_json(400, {"status": "error", "message": fehler})
                return

            result_id = schreibe_ergebnis(payload)
            self._sende_json(201, {"status": "created", "result_id": result_id})
            return

        if pfad == "/api/survey/questions":
            if not self._autorisierter_admin():
                return

            rolle = self._rolle_aus_query(parsed_url)
            if rolle is None:
                self._sende_json(400, {"status": "error", "message": "Unbekannte Rolle."})
                return

            umfrage = lade_umfrage(rolle)
            frage = self._lese_json_body()
            fehler = validiere_frage(frage, umfrage)
            if fehler:
                self._sende_json(400, {"status": "error", "message": fehler})
                return

            umfrage.setdefault("questions", []).append(frage)
            speichere_umfrage(rolle, umfrage)
            self._sende_json(201, {"status": "created", "question": frage})
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path
        prefix = "/api/survey/questions/"

        if not pfad.startswith(prefix):
            self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})
            return

        if not self._autorisierter_admin():
            return

        rolle = self._rolle_aus_query(parsed_url)
        if rolle is None:
            self._sende_json(400, {"status": "error", "message": "Unbekannte Rolle."})
            return

        frage_id = unquote(pfad[len(prefix):])
        umfrage = lade_umfrage(rolle)
        fragen = umfrage.get("questions", [])
        neue_fragen = [frage for frage in fragen if frage.get("id") != frage_id]

        if len(neue_fragen) == len(fragen):
            self._sende_json(404, {"status": "error", "message": "Frage nicht gefunden."})
            return

        umfrage["questions"] = neue_fragen
        speichere_umfrage(rolle, umfrage)
        self._sende_json(200, {"status": "deleted", "question_id": frage_id})

    def log_message(self, format, *args):
        """Schreibt Serverlogs in einem einfachen deutschsprachigen Format."""
        print(f"{self.address_string()} - {format % args}")


def starte_server(host="0.0.0.0", port=8000):
    """Startet den HTTP-Server fuer die Backend-API."""
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Ask-Alma-Backend laeuft auf http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    starte_server()
