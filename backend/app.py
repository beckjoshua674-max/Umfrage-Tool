import datetime
import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MOCK_DATA_DIR = BASE_DIR / "mock-data"
SURVEY_PATH = MOCK_DATA_DIR / "survey-questions.json"
RESULTS_DIR = DATA_DIR / "results"


def lade_umfrage():
    """Laedt die zentrale Umfragekonfiguration aus der Backend-Datenablage."""
    with SURVEY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


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

    return result_id


def validiere_ergebnis_payload(payload):
    """Prueft die Mindeststruktur fuer eingehende Umfrageantworten."""
    if not isinstance(payload, dict):
        return "Der Request-Body muss ein JSON-Objekt sein."

    if not isinstance(payload.get("survey_id"), str) or not payload["survey_id"].strip():
        return "Das Feld 'survey_id' muss als nicht-leerer String uebergeben werden."

    if "timestamp" in payload and not isinstance(payload["timestamp"], str):
        return "Das Feld 'timestamp' muss als ISO-8601-String uebergeben werden."

    if not isinstance(payload.get("answers"), dict):
        return "Das Feld 'answers' muss als Objekt mit Frage-IDs und Antworten uebergeben werden."

    umfrage = lade_umfrage()
    if payload["survey_id"] != umfrage["survey_id"]:
        return "Die uebergebene 'survey_id' ist fuer diese Backend-Konfiguration unbekannt."

    fragen = {frage["id"]: frage for frage in umfrage.get("questions", [])}
    fehlende_pflichtfragen = [
        frage_id
        for frage_id, frage in fragen.items()
        if frage.get("required") and not str(payload["answers"].get(frage_id, "")).strip()
    ]
    if fehlende_pflichtfragen:
        return f"Pflichtfragen ohne Antwort: {', '.join(fehlende_pflichtfragen)}."

    unbekannte_fragen = sorted(set(payload["answers"].keys()) - set(fragen.keys()))
    if unbekannte_fragen:
        return f"Unbekannte Frage-IDs: {', '.join(unbekannte_fragen)}."

    for frage_id, antwort in payload["answers"].items():
        frage = fragen[frage_id]
        if frage["type"] == "multiple_choice":
            erlaubte_werte = {option["value"] for option in frage.get("options", [])}
            if antwort not in erlaubte_werte:
                return f"Antwort fuer '{frage_id}' ist keine erlaubte Option."
        elif frage["type"] == "text" and not isinstance(antwort, str):
            return f"Antwort fuer '{frage_id}' muss ein String sein."

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

    def do_GET(self):
        pfad = urlparse(self.path).path

        if pfad == "/api/health":
            self._sende_json(200, {"status": "ok", "service": "ask-alma-backend"})
            return

        if pfad == "/api/survey":
            self._sende_json(200, lade_umfrage())
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_POST(self):
        pfad = urlparse(self.path).path

        if pfad != "/api/results":
            self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})
            return

        payload = self._lese_json_body()
        fehler = validiere_ergebnis_payload(payload)
        if fehler:
            self._sende_json(400, {"status": "error", "message": fehler})
            return

        result_id = schreibe_ergebnis(payload)
        self._sende_json(201, {"status": "created", "result_id": result_id})

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
