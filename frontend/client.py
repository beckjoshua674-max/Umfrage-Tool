# Ask Alma - Umfrage-Tool Frontend
# Website: http://127.0.0.1:5000/

import os
import json
import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'ask-alma-secret-key-dev'

# Konfiguration: URL des echten Backends (wird später von Codex bereitgestellt)
BACKEND_API_URL = "http://localhost:8000/api"


@app.route('/', methods=['GET'])
def index():
    """
    Startseite: Rollenauswahl (Admin, Professor, Student).
    """
    return render_template('role_select.html')


@app.route('/survey', methods=['GET'])
def survey():
    """
    Lädt die Umfrage. Der Rollen-Parameter bestimmt, welche Fragen das Backend liefert.
    """
    role = request.args.get('role', 'student')
    
    try:
        response = requests.get(f"{BACKEND_API_URL}/survey?role={role}")
        response.raise_for_status()
        survey_data = response.json()
    except Exception as e:
        print(f"Fehler: Backend nicht erreichbar ({e}). Zeige keine Fragen an.")
        survey_data = None
    
    return render_template('index.html', survey=survey_data, role=role)


@app.route('/submit', methods=['POST'])
def submit():
    """
    Nimmt die Formulardaten per klassischem HTML-POST entgegen, 
    wandelt sie in ein JSON-Objekt um und sendet sie an das Backend.
    """
    form_data = request.form.to_dict()
    survey_id = form_data.pop('survey_id', 'unknown_survey')
    
    payload = {
        "survey_id": survey_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "answers": form_data
    }
    
    try:
        response = requests.post(f"{BACKEND_API_URL}/results", json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Warnung: Fehler beim Senden an das Backend ({e}).")
        
    return render_template('success.html')


# ==============================================================
# Admin Dashboard & Verwaltung
# ==============================================================

@app.route('/admin', methods=['GET'])
def admin():
    """
    Admin-Dashboard: Zeigt alle Fragen und Ergebnisse.
    """
    # Fragen laden
    try:
        res_survey = requests.get(f"{BACKEND_API_URL}/survey")
        survey_data = res_survey.json() if res_survey.ok else None
    except Exception:
        survey_data = None
        
    # Ergebnisse laden
    try:
        res_results = requests.get(f"{BACKEND_API_URL}/results")
        results_data = res_results.json() if res_results.ok else None
    except Exception:
        results_data = None

    return render_template('admin.html', survey=survey_data, results=results_data)


@app.route('/admin/add_question', methods=['POST'])
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
    
    # Für V1 beim Multiple-Choice fiktive Optionen mitgeben
    if q_type == 'multiple_choice':
        payload['options'] = [
            {"value": "opt1", "text": "Option 1"},
            {"value": "opt2", "text": "Option 2"}
        ]

    try:
        response = requests.post(f"{BACKEND_API_URL}/survey/questions", json=payload)
        if response.ok:
            flash("Frage erfolgreich hinzugefügt.")
        else:
            flash(f"Backend meldet Fehler: {response.status_code}")
    except Exception as e:
        flash(f"Verbindungsfehler zum Backend: {e}")

    return redirect(url_for('admin'))


@app.route('/admin/delete_question/<question_id>', methods=['POST'])
def delete_question(question_id):
    """Proxy-Route zum Löschen einer Frage."""
    try:
        response = requests.delete(f"{BACKEND_API_URL}/survey/questions/{question_id}")
        if response.ok:
            flash("Frage erfolgreich gelöscht.")
        else:
            flash(f"Backend meldet Fehler: {response.status_code}")
    except Exception as e:
        flash(f"Verbindungsfehler zum Backend: {e}")

    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
