import base64
import csv
import datetime
import hashlib
import hmac
import io
import json
import os
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SURVEY_FILES = {
    "student": DATA_DIR / "survey_student.json",
    "professor": DATA_DIR / "survey_professor.json",
}
def lade_admin_zugangsdaten():
    """Liest die Admin-Zugangsdaten aus der JSON-Datei ein."""
    pfad = DATA_DIR / "admins.json"
    if not pfad.exists():
        return {}
    try:
        with pfad.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
JWT_SECRET = os.environ.get("ASK_ALMA_JWT_SECRET", "ask-alma-dev-secret").encode("utf-8")
JWT_LIFETIME_SECONDS = 60 * 60 * 8


def b64url_encode(data):
    """Kodiert Bytes fuer JWT ohne Padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data):
    """Dekodiert Base64Url-Daten mit ergaenztem Padding."""
    padding = "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def erstelle_jwt(username, role):
    """Erstellt ein einfaches HS256-JWT fuer den Admin-Login."""
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + JWT_LIFETIME_SECONDS,
    }
    header_b64 = b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signatur_basis = f"{header_b64}.{payload_b64}".encode("ascii")
    signatur = hmac.new(JWT_SECRET, signatur_basis, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{b64url_encode(signatur)}"


def pruefe_jwt(token):
    """Prueft Signatur, Ablaufzeit und Admin-Rolle eines JWT."""
    teile = token.split(".")
    if len(teile) != 3:
        return None

    signatur_basis = f"{teile[0]}.{teile[1]}".encode("ascii")
    erwartete_signatur = hmac.new(JWT_SECRET, signatur_basis, hashlib.sha256).digest()
    try:
        gegebene_signatur = b64url_decode(teile[2])
        payload = json.loads(b64url_decode(teile[1]).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not hmac.compare_digest(erwartete_signatur, gegebene_signatur):
        return None

    exp = payload.get("exp")
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    if isinstance(exp, int) and exp < now:
        return None

    return payload


def normalisiere_rolle(rolle):
    """Begrenzt Rollen auf die vorhandenen Umfragedateien."""
    rolle = (rolle or "student").strip().lower()
    if rolle not in SURVEY_FILES:
        return "student"
    return rolle


def lade_umfrage(rolle):
    """Laedt die Umfragedefinition fuer student oder professor."""
    pfad = SURVEY_FILES[normalisiere_rolle(rolle)]
    with pfad.open("r", encoding="utf-8") as file:
        return json.load(file)


def speichere_umfrage(rolle, daten):
    """Speichert eine Umfragedefinition in der passenden Rollendatei."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pfad = SURVEY_FILES[normalisiere_rolle(rolle)]
    with pfad.open("w", encoding="utf-8") as file:
        json.dump(daten, file, ensure_ascii=False, indent=2)
        file.write("\n")


def finde_umfrage_nach_id(survey_id):
    """Sucht eine Umfragedefinition anhand ihrer survey_id."""
    for rolle in SURVEY_FILES:
        try:
            umfrage = lade_umfrage(rolle)
        except FileNotFoundError:
            continue
        if umfrage.get("survey_id") == survey_id:
            return rolle, umfrage
    return None, None


def finde_umfrage_pfad_nach_id(survey_id):
    """Sucht den Dateipfad einer Umfrage anhand ihrer survey_id."""
    for rolle, pfad in SURVEY_FILES.items():
        if not pfad.exists():
            continue
        with pfad.open("r", encoding="utf-8") as file:
            daten = json.load(file)
        if daten.get("survey_id") == survey_id:
            return rolle, pfad
    return None, None


def validiere_umfrage_definition(payload):
    """Prueft eine vom Admin gespeicherte Umfragedefinition."""
    if not isinstance(payload, dict):
        return "Der Request-Body muss ein JSON-Objekt sein."
    for feld in ("survey_id", "role", "title", "questions"):
        if feld not in payload:
            return f"Das Pflichtfeld '{feld}' fehlt."
    if payload["role"] not in SURVEY_FILES:
        return "Das Feld 'role' muss 'student' oder 'professor' sein."
    if not isinstance(payload["questions"], list):
        return "Das Feld 'questions' muss eine Liste sein."

    erlaubte_typen = {"text", "single_choice", "multiple_choice", "rating"}
    for index, frage in enumerate(payload["questions"], start=1):
        if not isinstance(frage, dict):
            return f"Frage {index} muss ein Objekt sein."
        for feld in ("id", "type", "label", "required"):
            if feld not in frage:
                return f"Pflichtfeld '{feld}' fehlt in Frage {index}."
        if frage["type"] not in erlaubte_typen:
            return f"Ungueltiger Fragetyp in Frage {index}."
        if frage["type"] in {"single_choice", "multiple_choice"}:
            if not isinstance(frage.get("options"), list) or not frage["options"]:
                return f"Frage {index} benoetigt eine nicht-leere options-Liste."
    return None


def antwort_ist_leer(antwort):
    """Prueft leere Antworten typunabhaengig."""
    if antwort is None:
        return True
    if isinstance(antwort, list):
        return not any(str(wert).strip() for wert in antwort)
    return str(antwort).strip() == ""


def normalisiere_multiple_choice_antwort(antwort, erlaubte_werte):
    """Gibt Multiple-Choice-Antworten als Werteliste zurueck."""
    if isinstance(antwort, list):
        return [str(wert).strip() for wert in antwort if str(wert).strip()]
    if isinstance(antwort, str):
        if not antwort.strip():
            return []
        if antwort in erlaubte_werte:
            return [antwort]
        return zerlege_kommagetrennte_werte(antwort, erlaubte_werte)
    return None


def zerlege_kommagetrennte_werte(text, erlaubte_werte):
    """Rekonstruiert alte kommagetrennte Antworten anhand erlaubter Werte."""
    teile = [teil.strip() for teil in text.split(",")]
    werte = []
    index = 0
    while index < len(teile):
        treffer = None
        treffer_ende = index + 1
        for ende in range(len(teile), index, -1):
            kandidat = ",".join(teile[index:ende]).strip()
            if kandidat in erlaubte_werte:
                treffer = kandidat
                treffer_ende = ende
                break
        if treffer is None:
            return [wert.strip() for wert in text.split(",") if wert.strip()]
        werte.append(treffer)
        index = treffer_ende
    return werte


def formatiere_antwort_fuer_csv(antwort):
    """Serialisiert Listenantworten eindeutig fuer die CSV-Ablage."""
    if isinstance(antwort, list):
        werte = [str(wert).strip() for wert in antwort if str(wert).strip()]
        return json.dumps(werte, ensure_ascii=False, separators=(",", ":"))
    return antwort


def validiere_ergebnis_payload(payload):
    """Validiert Antworten gegen die gespeicherte Umfragedefinition."""
    if not isinstance(payload, dict):
        return "Der Payload muss ein valides JSON-Objekt sein."

    survey_id = payload.get("survey_id")
    answers = payload.get("answers")
    if not isinstance(survey_id, str) or not survey_id.strip():
        return "Das Feld 'survey_id' fehlt oder ist ungueltig."
    if not isinstance(answers, dict):
        return "Das Feld 'answers' fehlt oder ist ungueltig."

    _, umfrage = finde_umfrage_nach_id(survey_id)
    if umfrage is None:
        return f"Die uebergebene survey_id '{survey_id}' existiert nicht."

    fragen = {frage["id"]: frage for frage in umfrage.get("questions", [])}

    for frage_id, frage in fragen.items():
        antwort = answers.get(frage_id)
        if frage.get("required") and antwort_ist_leer(antwort):
            return f"Das Pflichtfeld '{frage_id}' wurde nicht ausgefuellt."

    for frage_id, antwort in answers.items():
        if frage_id not in fragen:
            return f"Die Frage-ID '{frage_id}' ist nicht vorhanden."

        frage = fragen[frage_id]
        typ = frage.get("type")
        if antwort_ist_leer(antwort):
            continue

        if typ == "single_choice":
            erlaubte_werte = {option["value"] for option in frage.get("options", [])}
            if antwort not in erlaubte_werte:
                return f"Ungueltiger Wert fuer Frage '{frage_id}'."
        elif typ == "multiple_choice":
            erlaubte_werte = {option["value"] for option in frage.get("options", [])}
            einzelwerte = normalisiere_multiple_choice_antwort(antwort, erlaubte_werte)
            if einzelwerte is None:
                return f"Antwort fuer Frage '{frage_id}' muss eine Liste oder Text sein."
            for wert in einzelwerte:
                if wert not in erlaubte_werte:
                    return f"Ungueltige Option '{wert}' fuer Frage '{frage_id}'."
        elif typ == "rating":
            try:
                zahl = int(antwort)
            except (TypeError, ValueError):
                return f"Bewertung fuer Frage '{frage_id}' muss eine Zahl von 1 bis 5 sein."
            if not 1 <= zahl <= 5:
                return f"Bewertung fuer Frage '{frage_id}' muss zwischen 1 und 5 liegen."
        elif typ == "text" and not isinstance(antwort, str):
            return f"Antwort fuer Frage '{frage_id}' muss Text sein."

    return None


def schreibe_ergebnis_csv(payload):
    """Speichert Antworten append-only in results_<survey_id>.csv."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result_id = str(uuid.uuid4())
    timestamp = payload.get("timestamp") or datetime.datetime.utcnow().isoformat() + "Z"
    csv_pfad = DATA_DIR / f"results_{payload['survey_id']}.csv"
    neue_datei = not csv_pfad.exists()

    with csv_pfad.open("a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if neue_datei:
            writer.writerow(["result_id", "timestamp", "survey_id", "question_id", "answer"])
        for frage_id, antwort in payload["answers"].items():
            writer.writerow([result_id, timestamp, payload["survey_id"], frage_id, formatiere_antwort_fuer_csv(antwort)])

    return result_id


def lade_ergebnisse_csv():
    """Liest alle Ergebnis-CSV-Dateien zusammen und gibt CSV-Text zurueck."""
    ausgabe = io.StringIO()
    writer = csv.writer(ausgabe, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(["result_id", "timestamp", "survey_id", "question_id", "answer"])

    for csv_pfad in sorted(DATA_DIR.glob("results_*.csv")):
        with csv_pfad.open("r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file, delimiter=";")
            next(reader, None)
            for zeile in reader:
                if len(zeile) >= 5:
                    writer.writerow(zeile[:5])

    return ausgabe.getvalue()


class ApiHandler(BaseHTTPRequestHandler):
    """HTTP-Handler fuer die Backend-API."""

    def _sende_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._sende_cors_header()
        self.end_headers()
        self.wfile.write(body)

    def _sende_cors_header(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")

    def _lese_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length == 0:
            return None
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return None

    def _admin_payload(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        payload = pruefe_jwt(auth_header.removeprefix("Bearer ").strip())
        if payload and payload.get("role") == "admin":
            return payload
        return None

    def _fordere_admin(self):
        if self._admin_payload() is None:
            self._sende_json(401, {"status": "error", "message": "Nicht autorisiert."})
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(200)
        self._sende_cors_header()
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path
        query = parse_qs(parsed_url.query)

        if pfad == "/api/health":
            self._sende_json(200, {"status": "ok", "service": "ask-alma-backend"})
            return

        if pfad == "/api/survey":
            survey_id = query.get("survey_id", [""])[0]
            if survey_id:
                _, umfrage = finde_umfrage_nach_id(survey_id)
                if umfrage is None:
                    self._sende_json(404, {"status": "error", "message": "Umfrage nicht gefunden."})
                    return
                self._sende_json(200, umfrage)
                return

            rolle = normalisiere_rolle(query.get("role", ["student"])[0])
            try:
                self._sende_json(200, lade_umfrage(rolle))
            except FileNotFoundError:
                self._sende_json(404, {"status": "error", "message": "Umfrage nicht gefunden."})
            return

        if pfad == "/api/results":
            if not self._fordere_admin():
                return
            csv_text = lade_ergebnisse_csv()
            body = csv_text.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self._sende_cors_header()
            self.end_headers()
            self.wfile.write(body)
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_POST(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path

        if pfad == "/api/login":
            payload = self._lese_json_body()
            username = payload.get("username") if isinstance(payload, dict) else None
            password = payload.get("password") if isinstance(payload, dict) else None
            admins = lade_admin_zugangsdaten()
            if username in admins and admins[username] == password:
                token = erstelle_jwt(username, "admin")
                self._sende_json(200, {"token": token, "role": "admin"})
                return
            self._sende_json(401, {"status": "error", "message": "Login fehlgeschlagen."})
            return

        if pfad == "/api/results":
            payload = self._lese_json_body()
            fehler = validiere_ergebnis_payload(payload)
            if fehler:
                self._sende_json(400, {"status": "error", "message": fehler})
                return
            result_id = schreibe_ergebnis_csv(payload)
            self._sende_json(201, {"status": "created", "result_id": result_id})
            return

        if pfad == "/api/surveys":
            if not self._fordere_admin():
                return
            payload = self._lese_json_body()
            fehler = validiere_umfrage_definition(payload)
            if fehler:
                self._sende_json(400, {"status": "error", "message": fehler})
                return
            speichere_umfrage(payload["role"], payload)
            self._sende_json(201, {"status": "created", "survey_id": payload["survey_id"]})
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_DELETE(self):
        pfad = urlparse(self.path).path
        prefix = "/api/surveys/"

        if not pfad.startswith(prefix):
            self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})
            return
        if not self._fordere_admin():
            return

        survey_id = unquote(pfad[len(prefix):]).strip()
        _, umfrage_pfad = finde_umfrage_pfad_nach_id(survey_id)
        if umfrage_pfad is None:
            self._sende_json(404, {"status": "error", "message": "Umfrage nicht gefunden."})
            return

        umfrage_pfad.unlink()
        self.send_response(204)
        self._sende_cors_header()
        self.end_headers()

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


def starte_server(host="0.0.0.0", port=8000):
    """Startet den HTTP-Server fuer die Backend-API."""
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Ask-Alma-Backend laeuft auf http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    starte_server()
