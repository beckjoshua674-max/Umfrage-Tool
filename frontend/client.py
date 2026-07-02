# Ask Alma - Umfrage-Tool Frontend
# Website: http://127.0.0.1:5000/

import os
import json
import datetime
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'ask-alma-secret-key-dev'

# Konfiguration: URL des echten Backends (wird später von Codex bereitgestellt)
BACKEND_API_URL = "http://localhost:8000/api"

# ==============================================================
# Helper & Authentifizierung (REST-Token via Web-Session)
# ==============================================================

def get_auth_headers():
    """Hilfsfunktion: Erstellt den Authorization-Header aus der Session."""
    token = session.get('token')
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def login_required(f):
    """Decorator: Leitet auf Login um, wenn kein Token in der Session liegt."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('token'):
            flash("Bitte loggen Sie sich ein, um fortzufahren.")
            return redirect(url_for('login_page', role=request.args.get('role', '')))
        return f(*args, **kwargs)
    return decorated_function

# Test-Zugangsdaten für den Entwicklungsmodus (solange das Backend /api/login noch nicht unterstützt)
DEV_TEST_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
}

# ==============================================================
# Routen: Login & Session
# ==============================================================

@app.route('/login', methods=['GET'])
def login_page():
    """Zeigt das Login-Formular an."""
    if session.get('token'):
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """Sendet Credentials an Backend und speichert JWT Token in der Session.
    Fallback: Wenn das Backend /api/login nicht bereitstellt, werden
    lokale Test-Zugangsdaten aus DEV_TEST_USERS akzeptiert."""
    username = request.form.get('username')
    password = request.form.get('password')
    desired_role = request.form.get('role', 'student')
    
    # Versuch 1: Login über das Backend (Produktivmodus)
    backend_erreichbar = False
    try:
        response = requests.post(f"{BACKEND_API_URL}/login", json={
            "username": username,
            "password": password
        }, timeout=3)
        backend_erreichbar = True
        
        if response.ok:
            data = response.json()
            session['token'] = data.get('token')
            session['role'] = data.get('role', desired_role)
            session['username'] = username
            flash("Erfolgreich eingeloggt.")
            
            if session['role'] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('survey', role=session['role']))
        
        # Backend hat geantwortet, aber Route existiert nicht (404) → Fallback nutzen
        if response.status_code == 404:
            backend_erreichbar = False
        else:
            flash("Login fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.")
            return redirect(url_for('login_page', role=desired_role))
            
    except Exception:
        backend_erreichbar = False
    
    # Versuch 2: Lokale Test-Zugangsdaten (Entwicklungsmodus)
    if not backend_erreichbar:
        test_user = DEV_TEST_USERS.get(username)
        if test_user and test_user["password"] == password:
            session['token'] = f"dev-token-{username}"
            session['role'] = test_user["role"]
            session['username'] = username
            flash(f"Eingeloggt als {username} (Entwicklungsmodus).")
            
            if test_user["role"] == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('survey', role=test_user["role"]))
    
    flash("Login fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.")
    return redirect(url_for('login_page', role=desired_role))

@app.route('/logout')
def logout():
    """Löscht das Token aus der Session."""
    session.clear()
    flash("Sie wurden abgemeldet.")
    return redirect(url_for('index'))

# ==============================================================
# Routen: Umfrage
# ==============================================================

@app.route('/', methods=['GET'])
def index():
    """Startseite: Rollenauswahl (Admin, Professor, Student)."""
    return render_template('role_select.html')

@app.route('/survey', methods=['GET'])
def survey():
    """Lädt die Umfrage und zeigt eine einzelne Frage basierend auf dem Schritt an."""
    role = request.args.get('role', 'student')
    step = request.args.get('step', 0, type=int)
    
    # Umfragedaten vom Backend laden und in der Session cachen
    # Beim ersten Aufruf (step=0) oder wenn keine Daten in der Session liegen
    if step == 0 or 'survey_data' not in session:
        try:
            response = requests.get(f"{BACKEND_API_URL}/survey?role={role}", headers=get_auth_headers())
            if response.status_code == 401:
                session.clear()
                flash("Ihre Sitzung ist abgelaufen. Bitte loggen Sie sich neu ein.")
                return redirect(url_for('login_page', role=role))
            response.raise_for_status()
            survey_data = response.json()
            # Umfrage und leeres Antwort-Dict in Session speichern
            session['survey_data'] = survey_data
            session['survey_role'] = role
            if step == 0:
                session['survey_answers'] = {}
        except Exception as e:
            print(f"Fehler beim Abrufen der Umfrage: {e}")
            return render_template('index.html', survey=None, role=role,
                                   question=None, step=0, total=0)
    
    survey_data = session.get('survey_data')
    if not survey_data:
        return render_template('index.html', survey=None, role=role,
                               question=None, step=0, total=0)
    
    questions = survey_data.get('questions', [])
    total = len(questions)
    
    # Sicherheitscheck: Schritt im gültigen Bereich?
    if step < 0 or step >= total:
        step = 0
    
    current_question = questions[step]
    # Bereits gespeicherte Antwort für diese Frage vorladen
    saved_answer = session.get('survey_answers', {}).get(current_question['id'], '')
    
    return render_template('index.html',
                           survey=survey_data,
                           question=current_question,
                           saved_answer=saved_answer,
                           step=step,
                           total=total,
                           role=role)

@app.route('/survey/next', methods=['POST'])
def survey_next():
    """Speichert die aktuelle Antwort in der Session und geht zur nächsten Frage."""
    role = request.form.get('role', 'student')
    step = request.form.get('step', 0, type=int)
    question_id = request.form.get('question_id', '')
    answer = request.form.get('answer', '').strip()
    
    # Antwort in Session speichern
    answers = session.get('survey_answers', {})
    if answer:
        answers[question_id] = answer
    session['survey_answers'] = answers
    
    survey_data = session.get('survey_data')
    if not survey_data:
        flash("Sitzung abgelaufen. Bitte starten Sie die Umfrage erneut.")
        return redirect(url_for('index'))
    
    total = len(survey_data.get('questions', []))
    next_step = step + 1
    
    # Letzte Frage erreicht? -> Absenden
    if next_step >= total:
        return redirect(url_for('survey_submit'))
    
    return redirect(url_for('survey', role=role, step=next_step))

@app.route('/survey/back', methods=['POST'])
def survey_back():
    """Speichert die aktuelle Antwort und geht eine Frage zurück."""
    role = request.form.get('role', 'student')
    step = request.form.get('step', 0, type=int)
    question_id = request.form.get('question_id', '')
    answer = request.form.get('answer', '').strip()
    
    # Auch beim Zurückgehen die aktuelle Antwort speichern
    answers = session.get('survey_answers', {})
    if answer:
        answers[question_id] = answer
    session['survey_answers'] = answers
    
    prev_step = max(0, step - 1)
    return redirect(url_for('survey', role=role, step=prev_step))

@app.route('/survey/submit', methods=['GET'])
def survey_submit():
    """Sendet alle gesammelten Antworten aus der Session an das Backend."""
    survey_data = session.get('survey_data')
    answers = session.get('survey_answers', {})
    
    if not survey_data:
        flash("Keine Umfragedaten gefunden. Bitte starten Sie erneut.")
        return redirect(url_for('index'))
    
    payload = {
        "survey_id": survey_data.get('survey_id', 'unknown'),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "answers": answers
    }
    
    try:
        requests.post(f"{BACKEND_API_URL}/results", json=payload, headers=get_auth_headers())
    except Exception as e:
        print(f"Warnung: Fehler beim Senden ({e}).")
    
    # Session-Daten der Umfrage bereinigen
    session.pop('survey_data', None)
    session.pop('survey_answers', None)
    session.pop('survey_role', None)
    
    return render_template('success.html')

# ==============================================================
# Routen: Admin Dashboard & Verwaltung
# ==============================================================

# Pfad zum Backend-Datenverzeichnis (für direkten Dateizugriff als Fallback)
import pathlib
BACKEND_DATEN_PFAD = pathlib.Path(__file__).parent.parent / "backend" / "data"

def lade_alle_umfragen_lokal():
    """Lädt alle bekannten Umfrage-Dateien direkt aus dem Backend-Datenverzeichnis.
    Dient als zuverlässiger Fallback, wenn der Backend-API-Endpunkt noch nicht implementiert ist."""
    import json as json_mod
    umfragen = []
    bekannte_rollen = [
        ("student", "survey_student.json"),
        ("professor", "survey_professor.json"),
    ]
    for rolle, dateiname in bekannte_rollen:
        pfad = BACKEND_DATEN_PFAD / dateiname
        if pfad.exists():
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    daten = json_mod.load(f)
                    daten["_rolle"] = rolle       # Interne Rolle für die Anzeige ergänzen
                    daten["_datei"] = dateiname   # Dateiname für Debugging-Zwecke
                    umfragen.append(daten)
            except Exception as e:
                print(f"Warnung: Konnte {dateiname} nicht laden: {e}")
    return umfragen

def lade_ergebnisse():
    """Versucht Ergebnisse vom Backend zu laden. Liest bei Fehler direkt aus dem Dateisystem."""
    import json as json_mod
    # Versuch 1: Backend-API
    try:
        res = requests.get(f"{BACKEND_API_URL}/results", headers=get_auth_headers(), timeout=2)
        if res.ok:
            return res.json()
    except Exception:
        pass

    # Versuch 2: Direkt aus dem Ergebnis-Verzeichnis lesen
    ergebnis_pfad = BACKEND_DATEN_PFAD / "results"
    if not ergebnis_pfad.exists():
        return []
    ergebnisse = []
    for datei in sorted(ergebnis_pfad.glob("*.json")):
        try:
            with open(datei, "r", encoding="utf-8") as f:
                ergebnisse.append(json_mod.load(f))
        except Exception:
            pass
    return ergebnisse

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    """Admin-Dashboard: Lädt alle Umfragen und Ergebnisse für die 3-Tab-Ansicht."""
    alle_umfragen = lade_alle_umfragen_lokal()
    alle_ergebnisse = lade_ergebnisse()
    return render_template('admin.html', umfragen=alle_umfragen, ergebnisse=alle_ergebnisse)

@app.route('/admin/surveys/save', methods=['POST'])
@login_required
def survey_save_local():
    """Speichert eine Umfrage direkt in die lokale JSON-Datei im Backend-Datenverzeichnis.
    Wird als Fallback genutzt, solange der Backend-Endpunkt /api/surveys/create noch nicht implementiert ist."""
    import json as json_mod

    nutzlast = request.get_json(silent=True)
    if not nutzlast:
        return json_mod.dumps({"status": "error", "message": "Kein gültiger JSON-Body empfangen."}), 400, {"Content-Type": "application/json"}

    rolle = nutzlast.get("role", "")
    if rolle not in ["student", "professor"]:
        return json_mod.dumps({"status": "error", "message": "Feld 'role' muss 'student' oder 'professor' sein."}), 400, {"Content-Type": "application/json"}

    dateiname = f"survey_{rolle}.json"
    ziel_pfad = BACKEND_DATEN_PFAD / dateiname

    # Versuch 1: Echten Backend-Endpunkt nutzen
    try:
        antwort = requests.post(
            f"{BACKEND_API_URL}/surveys/create",
            json=nutzlast,
            headers={**get_auth_headers(), "Content-Type": "application/json"},
            timeout=2
        )
        if antwort.ok:
            return antwort.text, antwort.status_code, {"Content-Type": "application/json"}
    except Exception:
        pass

    # Versuch 2: Direkt ins Dateisystem schreiben (Entwicklungsmodus)
    try:
        with open(ziel_pfad, "w", encoding="utf-8") as f:
            json_mod.dump(nutzlast, f, ensure_ascii=False, indent=2)
        return json_mod.dumps({
            "status": "created",
            "survey_id": nutzlast.get("survey_id", ""),
            "saved_as": dateiname
        }), 201, {"Content-Type": "application/json"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": f"Speichern fehlgeschlagen: {e}"}), 500, {"Content-Type": "application/json"}

@app.route('/admin/add_question', methods=['POST'])
@login_required
def add_question():
    """Proxy-Route zum Hinzufügen einer einzelnen Frage via Backend-API."""
    q_id = request.form.get('id')
    q_type = request.form.get('type')
    q_label = request.form.get('label')
    payload = {"id": q_id, "type": q_type, "label": q_label, "required": True}
    if q_type == 'multiple_choice':
        payload['options'] = [{"value": "opt1", "text": "Option 1"}, {"value": "opt2", "text": "Option 2"}]
    try:
        response = requests.post(f"{BACKEND_API_URL}/survey/questions", json=payload, headers=get_auth_headers())
        flash("Frage erfolgreich hinzugefügt." if response.ok else f"Backend Fehler: {response.status_code}")
    except Exception as e:
        flash(f"Verbindungsfehler: {e}")
    return redirect(url_for('admin'))

@app.route('/admin/delete_question/<question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    """Proxy-Route zum Löschen einer Frage via Backend-API."""
    try:
        response = requests.delete(f"{BACKEND_API_URL}/survey/questions/{question_id}", headers=get_auth_headers())
        flash("Frage erfolgreich gelöscht." if response.ok else f"Backend Fehler: {response.status_code}")
    except Exception as e:
        flash(f"Verbindungsfehler: {e}")
    return redirect(url_for('admin'))

@app.route('/admin/builder', methods=['GET'])
@login_required
def admin_builder():
    """Leitet auf das neue Admin-Dashboard weiter (Builder ist jetzt eingebettet)."""
    return redirect(url_for('admin'))

@app.route('/admin/surveys/create', methods=['POST'])
@login_required
def survey_create():
    """Alias für survey_save_local – für Kompatibilität mit dem Frontend-JS."""
    return survey_save_local()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
