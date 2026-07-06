import datetime
import json
import uuid
import base64
import hmac
import hashlib
import csv
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"

# JWT-Konfiguration (nur Standardbibliotheken erlaubt!)
JWT_SECRET = "ask-alma-super-secret-key-12345"
DEV_ADMIN_USER = "admin"
DEV_ADMIN_PASS = "admin123"

# ==============================================================
# JWT-Hilfsfunktionen (HMAC-SHA256, Base64Url-Encoding)
# ==============================================================

def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')

def b64url_decode(data: str) -> bytes:
    padding = '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def erstelle_jwt(payload: dict) -> str:
    """Erstellt ein standardkonformes JWT-Token unter Verwendung von HMAC-SHA256."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = b64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = b64url_encode(json.dumps(payload).encode('utf-8'))
    
    signatur_basis = f"{header_b64}.{payload_b64}".encode('utf-8')
    signatur = hmac.new(JWT_SECRET.encode('utf-8'), signatur_basis, hashlib.sha256).digest()
    signatur_b64 = b64url_encode(signatur)
    
    return f"{header_b64}.{payload_b64}.{signatur_b64}"

def verifiziere_jwt(token: str) -> dict:
    """Verifiziert ein JWT-Token. Gibt das Payload-Dictionary zurück oder None bei Fehlern."""
    try:
        teile = token.split('.')
        if len(teile) != 3:
            return None
        header_b64, payload_b64, signatur_b64 = teile
        
        signatur_basis = f"{header_b64}.{payload_b64}".encode('utf-8')
        erwartete_signatur = hmac.new(JWT_SECRET.encode('utf-8'), signatur_basis, hashlib.sha256).digest()
        erwartete_signatur_b64 = b64url_encode(erwartete_signatur)
        
        if not hmac.compare_digest(signatur_b64, erwartete_signatur_b64):
            return None
            
        payload = json.loads(b64url_decode(payload_b64).decode('utf-8'))
        return payload
    except Exception:
        return None

# ==============================================================
# Datenverwaltungs-Hilfsfunktionen (JSON & CSV)
# ==============================================================

def finde_umfragedatei_nach_id(survey_id: str) -> Path:
    """Sucht im data-Ordner nach einer JSON-Datei mit der passenden survey_id."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for pfad in DATA_DIR.glob("*.json"):
        try:
            with pfad.open("r", encoding="utf-8") as f:
                daten = json.load(f)
                if daten.get("survey_id") == survey_id:
                    return pfad
        except Exception:
            pass
    return None

def lade_umfrage_lokal(rolle: str) -> dict:
    """Lädt die Umfragedefinition anhand der Rolle (student|professor)."""
    dateiname = f"survey_{rolle}.json"
    pfad = DATA_DIR / dateiname
    if pfad.exists():
        try:
            with pfad.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def schreibe_ergebnis_csv(payload: dict) -> str:
    """Speichert Ergebnisse relational in einer CSV-Datei (results_<survey_id>.csv).
    Dies geschieht strikt append-only (Immutability by Design)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    survey_id = payload["survey_id"]
    csv_pfad = DATA_DIR / f"results_{survey_id}.csv"
    
    result_id = str(uuid.uuid4())
    zeitstempel = payload.get("timestamp") or datetime.datetime.utcnow().isoformat() + "Z"
    
    # Datei neu anlegen und Header schreiben falls sie noch nicht existiert
    neue_datei = not csv_pfad.exists()
    
    with csv_pfad.open("a", encoding="utf-8", newline="") as f:
        schreiber = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        if neue_datei:
            schreiber.writerow(['result_id', 'timestamp', 'survey_id', 'question_id', 'answer'])
        
        for question_id, antwort in payload["answers"].items():
            schreiber.writerow([result_id, zeitstempel, survey_id, question_id, antwort])
            
    return result_id

# ==============================================================
# Serverseitige Strikt-Validierung (Single Source of Truth)
# ==============================================================

def validiere_ergebnis_payload(payload: dict):
    """Führt eine strikte serverseitige Validierung des Ergebnisses durch."""
    if not isinstance(payload, dict):
        return "Der Payload muss ein valides JSON-Objekt sein."
        
    survey_id = payload.get("survey_id")
    if not isinstance(survey_id, str) or not survey_id.strip():
        return "Das Feld 'survey_id' fehlt oder ist ungültig."
        
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return "Das Feld 'answers' fehlt oder ist ungültig."
        
    # 1. Referenzielle Integrität prüfen (Existenz der survey_id)
    umfrage_pfad = finde_umfragedatei_nach_id(survey_id)
    if not umfrage_pfad:
        return f"Die übergebene survey_id '{survey_id}' existiert nicht im Dateisystem."
        
    try:
        with umfrage_pfad.open("r", encoding="utf-8") as f:
            umfrage_def = json.load(f)
    except Exception:
        return "Die Umfragedefinition konnte nicht geladen werden."
        
    fragen = {q["id"]: q for q in umfrage_def.get("questions", [])}
    
    # 2. Vollständigkeit (Pflichtfelder checken)
    for q_id, frage in fragen.items():
        antwort = answers.get(q_id)
        ist_leer = (antwort is None or str(antwort).strip() == "")
        if frage.get("required") and ist_leer:
            return f"Das Pflichtfeld '{q_id}' ('{frage.get('label')}') wurde nicht ausgefüllt."
            
    # 3. Wertebereichs-Prüfung (Domain check)
    for q_id, antwort in answers.items():
        if q_id not in fragen:
            return f"Die Frage-ID '{q_id}' ist in der Umfragedefinition nicht vorhanden."
            
        frage = fragen[q_id]
        typ = frage.get("type")
        
        # Antwort bei Pflichtfrage leer? (Bereits oben abgefangen, hier für optionale)
        if antwort is None or str(antwort).strip() == "":
            continue
            
        if typ == "single_choice":
            erlaubte_werte = [opt["value"] for opt in frage.get("options", [])]
            if antwort not in erlaubte_werte:
                return f"Ungültiger Wert für Frage '{q_id}': '{antwort}'. Erlaubt sind: {erlaubte_werte}"
                
        elif typ == "multiple_choice":
            # Bei Mehrfachauswahl sind die Antworten kommasepariert
            erlaubte_werte = [opt["value"] for opt in frage.get("options", [])]
            einzel_antworten = [a.strip() for a in antwort.split(',') if a.strip()]
            if not einzel_antworten and frage.get("required"):
                return f"Das Pflichtfeld '{q_id}' erfordert mindestens eine Option."
            for a in einzel_antworten:
                if a not in erlaubte_werte:
                    return f"Ungültige Option '{a}' für Frage '{q_id}'. Erlaubt sind: {erlaubte_werte}"
                    
        elif typ == "rating":
            try:
                zahl = int(antwort)
                if zahl < 1 or zahl > 5:
                    return f"Ungültige Bewertung für Frage '{q_id}': {zahl}. Erlaubt ist 1-5."
            except ValueError:
                return f"Bewertung für Frage '{q_id}' muss eine Ganzzahl zwischen 1 und 5 sein."
                
    return None

# ==============================================================
# REST API Handler
# ==============================================================

class ApiHandler(BaseHTTPRequestHandler):
    
    def _sende_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")  # CORS für verteilte Setups
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
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

    def _validiere_admin_auth(self) -> dict:
        """Prüft den Authorization Header. Gibt das JWT-Payload bei Erfolg zurück, sonst None."""
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ")[1]
        payload = verifiziere_jwt(token)
        if payload and payload.get("role") == "admin":
            return payload
        return None

    def do_OPTIONS(self):
        """CORS-Preflight-Requests abfangen."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path

        # 1. Health Endpoint
        if pfad == "/api/health":
            self._sende_json(200, {"status": "ok", "service": "ask-alma-backend"})
            return

        # 2. GET Umfrage (Rollenbasierter Abruf)
        if pfad == "/api/survey":
            query_params = parse_qs(parsed_url.query)
            rolle = query_params.get("role", ["student"])[0]
            if rolle not in ["student", "professor"]:
                rolle = "student"
                
            umfrage_daten = lade_umfrage_lokal(rolle)
            if umfrage_daten:
                self._sende_json(200, umfrage_daten)
            else:
                self._sende_json(404, {"status": "error", "message": f"Keine Umfrage für die Rolle '{rolle}' gefunden."})
            return

        # 3. GET Ergebnisse (Admin geschützt)
        if pfad == "/api/results":
            admin_payload = self._validiere_admin_auth()
            if not admin_payload:
                self._sende_json(401, {"status": "error", "message": "Nicht autorisiert."})
                return
                
            # Alle CSV-Dateien im data-Ordner einlesen und zusammenführen
            ausgabe = io.StringIO()
            schreiber = csv.writer(ausgabe, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            schreiber.writerow(['result_id', 'timestamp', 'survey_id', 'question_id', 'answer'])
            
            geschriebene_zeilen = 0
            for csv_pfad in DATA_DIR.glob("results_*.csv"):
                try:
                    with csv_pfad.open("r", encoding="utf-8") as f:
                        leser = csv.reader(f, delimiter=';')
                        try:
                            next(leser)  # Header überspringen
                        except StopIteration:
                            continue
                        for zeile in leser:
                            if len(zeile) >= 5:
                                schreiber.writerow(zeile)
                                geschriebene_zeilen += 1
                except Exception:
                    pass
            
            body = ausgabe.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_POST(self):
        pfad = urlparse(self.path).path

        # 1. Admin Login
        if pfad == "/api/login":
            payload = self._lese_json_body()
            if not payload or "username" not in payload or "password" not in payload:
                self._sende_json(400, {"status": "error", "message": "Benutzername und Passwort erforderlich."})
                return
                
            if payload["username"] == DEV_ADMIN_USER and payload["password"] == DEV_ADMIN_PASS:
                token = erstelle_jwt({"role": "admin", "username": DEV_ADMIN_USER, "exp": str(datetime.datetime.utcnow() + datetime.timedelta(hours=2))})
                self._sende_json(200, {"token": token, "role": "admin"})
            else:
                self._sende_json(401, {"status": "error", "message": "Ungültiger Benutzername oder Passwort."})
            return

        # 2. Umfrage anlegen / ändern (Admin geschützt)
        if pfad == "/api/surveys":
            admin_payload = self._validiere_admin_auth()
            if not admin_payload:
                self._sende_json(401, {"status": "error", "message": "Nicht autorisiert."})
                return
                
            payload = self._lese_json_body()
            if not payload or "survey_id" not in payload or "role" not in payload or "title" not in payload:
                self._sende_json(400, {"status": "error", "message": "Ungültige Definition: survey_id, role und title sind erforderlich."})
                return
                
            rolle = payload["role"]
            if rolle not in ["student", "professor"]:
                self._sende_json(400, {"status": "error", "message": "Zielgruppe/Rolle muss 'student' oder 'professor' sein."})
                return
                
            # Persistent als JSON speichern
            dateiname = f"survey_{rolle}.json"
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            zielpfad = DATA_DIR / dateiname
            
            try:
                with zielpfad.open("w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
                self._sende_json(201, {"status": "created", "survey_id": payload["survey_id"]})
            except Exception as e:
                self._sende_json(500, {"status": "error", "message": f"Speichern fehlgeschlagen: {e}"})
            return

        # 3. Ergebnisse einreichen
        if pfad == "/api/results":
            payload = self._lese_json_body()
            fehler = validiere_ergebnis_payload(payload)
            if fehler:
                self._sende_json(400, {"status": "error", "message": fehler})
                return
                
            try:
                result_id = schreibe_ergebnis_csv(payload)
                self._sende_json(201, {"status": "created", "result_id": result_id})
            except Exception as e:
                self._sende_json(500, {"status": "error", "message": f"Speichern fehlgeschlagen: {e}"})
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def do_DELETE(self):
        parsed_url = urlparse(self.path)
        pfad = parsed_url.path

        # 1. DELETE Umfrage (Admin geschützt)
        # Pfad-Format: /api/surveys/{survey_id}
        if pfad.startswith("/api/surveys/"):
            admin_payload = self._validiere_admin_auth()
            if not admin_payload:
                self._sende_json(401, {"status": "error", "message": "Nicht autorisiert."})
                return
                
            survey_id = pfad.replace("/api/surveys/", "").strip()
            if not survey_id:
                self._sende_json(400, {"status": "error", "message": "survey_id erforderlich."})
                return
                
            umfrage_pfad = finde_umfragedatei_nach_id(survey_id)
            if umfrage_pfad and umfrage_pfad.exists():
                try:
                    umfrage_pfad.unlink()
                    # 204 No Content
                    self.send_response(204)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                except Exception as e:
                    self._sende_json(500, {"status": "error", "message": f"Löschen fehlgeschlagen: {e}"})
            else:
                self._sende_json(404, {"status": "error", "message": f"Umfrage mit ID '{survey_id}' nicht gefunden."})
            return

        self._sende_json(404, {"status": "error", "message": "Route nicht gefunden."})

    def log_message(self, format, *args):
        """Standardlogformat verwenden."""
        print(f"{self.address_string()} - {format % args}")

def starte_server(host="0.0.0.0", port=8000):
    server = ThreadingHTTPServer((host, port), ApiHandler)
    print(f"Ask-Alma-Backend läuft auf http://{host}:{port}")
    server.serve_forever()

if __name__ == "__main__":
    starte_server()
