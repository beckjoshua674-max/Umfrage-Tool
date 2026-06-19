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
    """Sendet Credentials an Backend und speichert JWT Token in der Session."""
    username = request.form.get('username')
    password = request.form.get('password')
    desired_role = request.form.get('role', 'student')
    
    try:
        response = requests.post(f"{BACKEND_API_URL}/login", json={
            "username": username,
            "password": password
        })
        
        if response.ok:
            data = response.json()
            session['token'] = data.get('token')
            session['username'] = username
            flash("Erfolgreich eingeloggt.")
            
            # Routing nach erfolgreichem Login
            if desired_role == 'admin':
                return redirect(url_for('admin'))
            else:
                return redirect(url_for('survey', role=desired_role))
        else:
            flash("Login fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.")
            return redirect(url_for('login_page', role=desired_role))
            
    except Exception as e:
        flash(f"Fehler: Backend nicht erreichbar ({e}).")
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
    """Lädt die Umfrage spezifisch für die gewählte Rolle."""
    role = request.args.get('role', 'student')
    
    try:
        response = requests.get(f"{BACKEND_API_URL}/survey?role={role}", headers=get_auth_headers())
        if response.status_code == 401:
            session.clear()
            flash("Ihre Sitzung ist abgelaufen. Bitte loggen Sie sich neu ein.")
            return redirect(url_for('login_page', role=role))
            
        response.raise_for_status()
        survey_data = response.json()
    except Exception as e:
        print(f"Fehler beim Abrufen der Umfrage: {e}")
        survey_data = None
    
    return render_template('index.html', survey=survey_data, role=role)

@app.route('/submit', methods=['POST'])
def submit():
    """Sendet ausgefüllte Umfrage an Backend."""
    form_data = request.form.to_dict()
    survey_id = form_data.pop('survey_id', 'unknown_survey')
    
    payload = {
        "survey_id": survey_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "answers": form_data
    }
    
    try:
        requests.post(f"{BACKEND_API_URL}/results", json=payload, headers=get_auth_headers())
    except Exception as e:
        print(f"Warnung: Fehler beim Senden ({e}).")
        
    return render_template('success.html')

# ==============================================================
# Routen: Admin Dashboard & Verwaltung
# ==============================================================

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    """Admin-Dashboard: Lädt alle Fragen und Ergebnisse."""
    try:
        res_survey = requests.get(f"{BACKEND_API_URL}/survey", headers=get_auth_headers())
        survey_data = res_survey.json() if res_survey.ok else None
    except Exception:
        survey_data = None
        
    try:
        res_results = requests.get(f"{BACKEND_API_URL}/results", headers=get_auth_headers())
        results_data = res_results.json() if res_results.ok else None
    except Exception:
        results_data = None

    return render_template('admin.html', survey=survey_data, results=results_data)

@app.route('/admin/add_question', methods=['POST'])
@login_required
def add_question():
    """Proxy-Route zum Hinzufügen einer Frage."""
    q_id = request.form.get('id')
    q_type = request.form.get('type')
    q_label = request.form.get('label')
    
    payload = {
        "id": q_id,
        "type": q_type,
        "label": q_label,
        "required": True
    }
    
    if q_type == 'multiple_choice':
        payload['options'] = [
            {"value": "opt1", "text": "Option 1"},
            {"value": "opt2", "text": "Option 2"}
        ]

    try:
        response = requests.post(f"{BACKEND_API_URL}/survey/questions", json=payload, headers=get_auth_headers())
        if response.ok:
            flash("Frage erfolgreich hinzugefügt.")
        else:
            flash(f"Backend Fehler: {response.status_code}")
    except Exception as e:
        flash(f"Verbindungsfehler: {e}")

    return redirect(url_for('admin'))

@app.route('/admin/delete_question/<question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    """Proxy-Route zum Löschen einer Frage."""
    try:
        response = requests.delete(f"{BACKEND_API_URL}/survey/questions/{question_id}", headers=get_auth_headers())
        if response.ok:
            flash("Frage erfolgreich gelöscht.")
        else:
            flash(f"Backend Fehler: {response.status_code}")
    except Exception as e:
        flash(f"Verbindungsfehler: {e}")

    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
