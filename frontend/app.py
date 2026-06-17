# Ask Alma - Umfrage-Tool Frontend

import os
import json
import datetime
import requests
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'ask-alma-secret-key-dev'

# Konfiguration: URL des echten Backends (wird später von Codex bereitgestellt)
BACKEND_API_URL = "http://localhost:8000/api"

def get_mock_survey():
    """
    Lädt Beispieldaten aus der lokalen JSON-Datei.
    Wird als Fallback genutzt, solange das echte Backend noch nicht läuft.
    """
    mock_path = os.path.join(os.path.dirname(__file__), 'mock-data', 'survey-questions.json')
    try:
        with open(mock_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback, falls die mock-data Datei nicht existiert
        return {
            "survey_id": "ask_alma_eval_v1",
            "title": "Ask Alma - Evaluation",
            "description": "Umfrage-Tool der Hochschule Kehl zur Evaluation des Nutzens von Ask Alma.",
            "questions": [
                {
                    "id": "q1",
                    "type": "text",
                    "label": "1. Welche Erfahrungen haben Sie bisher mit dem Tool \"Ask Alma\" gemacht?",
                    "required": True
                }
            ]
        }

@app.route('/', methods=['GET'])
def index():
    """
    Hauptroute für das Frontend.
    Holt die Umfragekonfiguration vom Backend (bzw. Mock) und rendert das HTML-Template.
    """
    # Versuche die Umfrage vom echten Backend (Codex) zu laden
    try:
        response = requests.get(f"{BACKEND_API_URL}/survey")
        response.raise_for_status()
        survey_data = response.json()
    except Exception as e:
        print(f"Warnung: Backend nicht erreichbar ({e}). Lade lokales Mock-up.")
        survey_data = get_mock_survey()
    
    return render_template('index.html', survey=survey_data)


@app.route('/submit', methods=['POST'])
def submit():
    """
    Nimmt die Formulardaten per klassischem HTML-POST entgegen, 
    wandelt sie in ein JSON-Objekt um und sendet sie an das Backend.
    """
    form_data = request.form.to_dict()
    
    # Extrahiere die survey_id (wird als Hidden-Field übergeben)
    survey_id = form_data.pop('survey_id', 'unknown_survey')
    
    payload = {
        "survey_id": survey_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "answers": form_data
    }
    
    print("Daten für Backend vorbereitet:", json.dumps(payload, indent=2))
    
    # Sende die gesammelten Antworten an das Backend (Codex)
    try:
        response = requests.post(f"{BACKEND_API_URL}/results", json=payload)
        response.raise_for_status()
        print("Erfolgreich an das Backend gesendet!")
    except Exception as e:
        print(f"Warnung: Fehler beim Senden an das Backend ({e}). "
              f"Stellen Sie sicher, dass der Backend-Server von Codex läuft.")
        # Wir zeigen vorerst trotzdem die Erfolgsseite, um den Nutzer nicht zu blockieren,
        # solange sich das Backend noch in Entwicklung befindet.
        
    return render_template('success.html')

if __name__ == '__main__':
    # Startet den Entwicklungsserver auf Port 5000
    app.run(debug=True, host='0.0.0.0', port=5000)
