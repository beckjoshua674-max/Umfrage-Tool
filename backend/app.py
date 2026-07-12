import csv
import datetime
import json
import os
import uuid
import contextlib
import time
import io
from functools import wraps
from pathlib import Path
import jwt
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Versuche .env-Datei einzulesen, falls vorhanden
env_pfad = BASE_DIR / ".env"
if env_pfad.exists():
    try:
        with env_pfad.open("r", encoding="utf-8") as env_file:
            for zeile in env_file:
                zeile = zeile.strip()
                if zeile and not zeile.startswith("#") and "=" in zeile:
                    k, v = zeile.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"Fehler beim Laden der .env Datei: {e}")

JWT_SECRET = os.environ.get("ASK_ALMA_JWT_SECRET", "ask-alma-dev-secret")
JWT_LIFETIME_SECONDS = 60 * 60 * 8

app = Flask(__name__)
CORS(app)  # Erlaubt CORS für die gesamte API

def lade_admin_zugangsdaten():
    pfad = DATA_DIR / "admins.json"
    if not pfad.exists():
        return {}
    try:
        with pfad.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def lade_links():
    pfad = DATA_DIR / "links.json"
    if not pfad.exists():
        return {}
    try:
        with pfad.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def speichere_links(links):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pfad = DATA_DIR / "links.json"
    with pfad.open("w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False, indent=2)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"status": "error", "message": "Nicht autorisiert."}), 401
        
        token = auth_header.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("role") != "admin":
                return jsonify({"status": "error", "message": "Nicht autorisiert."}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"status": "error", "message": "Token abgelaufen."}), 401
        except jwt.InvalidTokenError:
            return jsonify({"status": "error", "message": "Ungültiges Token."}), 401
        
        return f(*args, **kwargs)
    return decorated

# --- Datei & Logik Funktionen ---

def speichere_umfrage(daten):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    survey_id = daten.get("survey_id")
    sichere_id = "".join(c for c in survey_id if c.isalnum() or c in ("_", "-"))
    pfad = DATA_DIR / f"survey_{sichere_id}.json"
    with pfad.open("w", encoding="utf-8") as file:
        json.dump(daten, file, ensure_ascii=False, indent=2)
        file.write("\n")

def finde_umfrage_nach_id(survey_id):
    for pfad in DATA_DIR.glob("survey_*.json"):
        try:
            with pfad.open("r", encoding="utf-8") as file:
                umfrage = json.load(file)
                if umfrage.get("survey_id") == survey_id:
                    return None, umfrage
        except Exception:
            continue
    return None, None

def finde_umfrage_pfad_nach_id(survey_id):
    for pfad in DATA_DIR.glob("survey_*.json"):
        try:
            with pfad.open("r", encoding="utf-8") as file:
                daten = json.load(file)
                if daten.get("survey_id") == survey_id:
                    return None, pfad
        except Exception:
            continue
    return None, None

def lade_alle_umfragen():
    umfragen = []
    for pfad in DATA_DIR.glob("survey_*.json"):
        try:
            with pfad.open("r", encoding="utf-8") as file:
                umfragen.append(json.load(file))
        except Exception:
            continue
    return umfragen

def validiere_umfrage_definition(payload):
    if not isinstance(payload, dict):
        return "Der Request-Body muss ein JSON-Objekt sein."
    for feld in ("survey_id", "title", "questions"):
        if feld not in payload:
            return f"Das Pflichtfeld '{feld}' fehlt."
    if not isinstance(payload["questions"], list):
        return "Das Feld 'questions' muss eine Liste sein."

    erlaubte_typen = {"text", "single_choice", "multiple_choice", "rating", "yes_no", "date"}
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
    if antwort is None:
        return True
    if isinstance(antwort, list):
        return not any(str(wert).strip() for wert in antwort)
    return str(antwort).strip() == ""

def zerlege_kommagetrennte_werte(text, erlaubte_werte):
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

def normalisiere_multiple_choice_antwort(antwort, erlaubte_werte):
    if isinstance(antwort, list):
        return [str(wert).strip() for wert in antwort if str(wert).strip()]
    if isinstance(antwort, str):
        text = antwort.strip()
        if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
            text = text[1:-1].strip()
        
        if text.startswith("[") and text.endswith("]"):
            try:
                import json as json_mod
                werte = json_mod.loads(text.replace("'", '"'))
                if isinstance(werte, list):
                    return [str(wert).strip() for wert in werte if str(wert).strip()]
            except Exception:
                innen = text[1:-1].strip()
                if innen:
                    teile = [t.strip().strip("'").strip('"') for t in innen.split(",")]
                    return [t for t in teile if t]
                return []

        if not text:
            return []
        if text in erlaubte_werte:
            return [text]
        return zerlege_kommagetrennte_werte(text, erlaubte_werte)
    return None

def validiere_ergebnis_payload(payload):
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
        elif typ == "yes_no" and antwort not in ("ja", "nein"):
            return f"Wert fuer Ja/Nein-Frage '{frage_id}' muss 'ja' oder 'nein' sein."
        elif typ == "date" and (not isinstance(antwort, str) or not antwort.strip()):
            return f"Antwort fuer Datum-Frage '{frage_id}' muss ein gueltiges Datum sein."
    return None

def formatiere_antwort_fuer_csv(antwort):
    if isinstance(antwort, list):
        werte = [str(wert).strip() for wert in antwort if str(wert).strip()]
        werte_clean = [w.replace(';', ',').replace('\n', ' ').replace('\r', ' ') for w in werte]
        return json.dumps(werte_clean, ensure_ascii=False, separators=(",", ":"))
    if isinstance(antwort, str):
        return antwort.replace(';', ',').replace('\n', ' ').replace('\r', ' ')
    return antwort

@contextlib.contextmanager
def datei_sperre_einfach(lock_pfad):
    start_time = time.time()
    while True:
        try:
            fd = os.open(lock_pfad, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            if time.time() - start_time > 5.0:
                break
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.remove(lock_pfad)
        except Exception:
            pass

def schreibe_ergebnis_csv(payload):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result_id = str(uuid.uuid4())
    timestamp = payload.get("timestamp") or datetime.datetime.utcnow().isoformat() + "Z"
    csv_pfad = DATA_DIR / f"results_{payload['survey_id']}.csv"
    lock_pfad = DATA_DIR / f"results_{payload['survey_id']}.csv.lock"
    neue_datei = not csv_pfad.exists()

    with datei_sperre_einfach(lock_pfad):
        with csv_pfad.open("a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL)
            if neue_datei:
                writer.writerow(["result_id", "timestamp", "survey_id", "question_id", "answer"])
            for frage_id, antwort in payload["answers"].items():
                writer.writerow([result_id, timestamp, payload["survey_id"], frage_id, formatiere_antwort_fuer_csv(antwort)])

    return result_id

def lade_ergebnisse_csv():
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

# --- API Endpunkte ---

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "ask-alma-backend"})

@app.route("/api/login", methods=["POST"])
def login():
    payload = request.json or {}
    username = payload.get("username")
    password = payload.get("password")
    admins = lade_admin_zugangsdaten()
    if username in admins and admins[username] == password:
        now = datetime.datetime.now(datetime.timezone.utc)
        token = jwt.encode({
            "username": username,
            "role": "admin",
            "iat": now,
            "exp": now + datetime.timedelta(seconds=JWT_LIFETIME_SECONDS)
        }, JWT_SECRET, algorithm="HS256")
        return jsonify({"token": token, "role": "admin"}), 200
    return jsonify({"status": "error", "message": "Login fehlgeschlagen."}), 401

@app.route("/api/surveys", methods=["GET"])
def get_surveys():
    """Gibt eine Liste aller Umfragen zurück (REST Standard)."""
    return jsonify(lade_alle_umfragen()), 200

@app.route("/api/surveys/<survey_id>", methods=["GET"])
def get_survey(survey_id):
    """Gibt eine spezifische Umfrage zurück."""
    _, umfrage = finde_umfrage_nach_id(survey_id)
    if not umfrage:
        return jsonify({"status": "error", "message": "Umfrage nicht gefunden."}), 404
    return jsonify(umfrage), 200

@app.route("/api/surveys", methods=["POST"])
@token_required
def create_survey():
    """Erstellt eine neue Umfrage."""
    payload = request.json or {}
    if not payload.get("survey_id"):
        payload["survey_id"] = str(uuid.uuid4())
    
    fehler = validiere_umfrage_definition(payload)
    if fehler:
        return jsonify({"status": "error", "message": fehler}), 400
    
    _, exists = finde_umfrage_nach_id(payload["survey_id"])
    if exists:
        return jsonify({"status": "error", "message": "Umfrage mit dieser ID existiert bereits. Nutze PUT zum Aktualisieren."}), 409
    
    speichere_umfrage(payload)
    resp = jsonify({"status": "created", "survey_id": payload["survey_id"]})
    resp.headers["Location"] = f"/api/surveys/{payload['survey_id']}"
    return resp, 201

@app.route("/api/surveys/<survey_id>", methods=["PUT"])
@token_required
def update_survey(survey_id):
    """Aktualisiert eine bestehende Umfrage (oder erstellt sie, falls Idempotenz gewünscht ist)."""
    payload = request.json or {}
    payload["survey_id"] = survey_id
    fehler = validiere_umfrage_definition(payload)
    if fehler:
        return jsonify({"status": "error", "message": fehler}), 400
    
    speichere_umfrage(payload)
    return jsonify({"status": "updated", "survey_id": survey_id}), 200

@app.route("/api/surveys/<survey_id>", methods=["DELETE"])
@token_required
def delete_survey(survey_id):
    """Löscht eine spezifische Umfrage."""
    _, umfrage_pfad = finde_umfrage_pfad_nach_id(survey_id)
    if not umfrage_pfad:
        return jsonify({"status": "error", "message": "Umfrage nicht gefunden."}), 404
    umfrage_pfad.unlink()
    return "", 204

@app.route("/api/results", methods=["POST"])
def submit_results():
    """Speichert Ergebnisse als CSV."""
    payload = request.json or {}
    fehler = validiere_ergebnis_payload(payload)
    if fehler:
        return jsonify({"status": "error", "message": fehler}), 400
    result_id = schreibe_ergebnis_csv(payload)
    return jsonify({"status": "created", "result_id": result_id}), 201

@app.route("/api/results", methods=["GET"])
@token_required
def get_results():
    """Gibt alle Ergebnisse als CSV zurück."""
    csv_text = lade_ergebnisse_csv()
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
        }
    )

@app.route("/api/links", methods=["GET"])
def get_links():
    """Gibt alle Links zurück."""
    return jsonify(lade_links()), 200

@app.route("/api/links", methods=["POST"])
@token_required
def create_link():
    """Erstellt einen neuen Link für bestimmte Umfragen."""
    payload = request.json or {}
    surveys = payload.get("surveys", [])
    if not isinstance(surveys, list):
        return jsonify({"status": "error", "message": "surveys muss eine Liste sein."}), 400
    
    links = lade_links()
    token = uuid.uuid4().hex[:8]  # Kurzer 8-stelliger Token
    links[token] = surveys
    speichere_links(links)
    return jsonify({"status": "created", "link_id": token}), 201

@app.route("/api/links/<link_id>", methods=["DELETE"])
@token_required
def delete_link(link_id):
    """Löscht einen Link."""
    links = lade_links()
    if link_id in links:
        del links[link_id]
        speichere_links(links)
        return "", 204
    return jsonify({"status": "error", "message": "Link nicht gefunden."}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
