# Ask Alma - Umfrage-Tool Frontend
# Website: http://127.0.0.1:5000/

import datetime
import os

import requests
from flask import Flask, flash, redirect, render_template, request, url_for


app = Flask(__name__)
app.secret_key = "ask-alma-secret-key-dev"

# Konfiguration: URL der Backend-Schnittstelle.
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000/api")


@app.route("/", methods=["GET"])
def index():
    """
    Hauptroute fuer das Frontend.
    Holt die Umfragekonfiguration vom Backend und rendert das HTML-Template.
    """
    try:
        response = requests.get(f"{BACKEND_API_URL}/survey", timeout=5)
        response.raise_for_status()
        survey_data = response.json()
    except Exception as e:
        print(f"Fehler: Backend-Schnittstelle nicht erreichbar ({e}).")
        flash("Die Umfrage konnte nicht vom Backend geladen werden.")
        survey_data = {
            "survey_id": "",
            "title": "Ask Alma - Evaluation",
            "description": "Backend-Schnittstelle nicht erreichbar.",
            "questions": [],
        }

    return render_template("index.html", survey=survey_data)


@app.route("/submit", methods=["POST"])
def submit():
    """
    Nimmt die Formulardaten per HTML-POST entgegen,
    wandelt sie in ein JSON-Objekt um und sendet sie an das Backend.
    """
    form_data = request.form.to_dict()

    # Extrahiere die survey_id, die als Hidden-Field uebergeben wird.
    survey_id = form_data.pop("survey_id", "unknown_survey")

    payload = {
        "survey_id": survey_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "answers": form_data,
    }

    print("Daten fuer Backend vorbereitet:", payload)

    try:
        response = requests.post(f"{BACKEND_API_URL}/results", json=payload, timeout=5)
        response.raise_for_status()
        print("Erfolgreich an das Backend gesendet.")
    except Exception as e:
        print(f"Fehler beim Senden an das Backend ({e}).")
        flash("Ihre Antworten konnten nicht an das Backend gesendet werden.")
        return redirect(url_for("index"))

    return render_template("success.html")


if __name__ == "__main__":
    # Startet den Entwicklungsserver auf Port 5000.
    app.run(debug=True, host="0.0.0.0", port=5000)
