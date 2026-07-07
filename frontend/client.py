# Ask Alma - Umfrage-Tool Frontend
# Website: http://127.0.0.1:5000/

import os
import json
import datetime
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response

app = Flask(__name__)
app.secret_key = 'ask-alma-secret-key-dev'
app.json.ensure_ascii = False
app.config['JSON_AS_ASCII'] = False


@app.before_request
def auto_logout_admin_on_leave():
    """LÃ¶scht die Session automatisch, wenn ein Admin die Admin-Ansicht verlÃ¤sst."""
    if session.get('role') == 'admin':
        pfad = request.path
        # Wenn der Pfad nicht mit /admin beginnt und auch nicht /logout, /static oder /favicon.ico ist,
        # wird die Session gelÃ¶scht (automatischer Logout bei URL-Wechsel).
        if not pfad.startswith('/admin') and not pfad.startswith('/api') and pfad not in ['/logout', '/favicon.ico'] and not pfad.startswith('/static'):
            session.clear()
            flash("Ihre Administrator-Sitzung wurde beim Verlassen der Admin-Ansicht automatisch beendet.")


# Konfiguration: URL des echten Backends (wird spÃ¤ter von Codex bereitgestellt)
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

# Test-Zugangsdaten fÃ¼r den Entwicklungsmodus (solange das Backend /api/login noch nicht unterstÃ¼tzt)
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
    Fallback: Wenn das Backend /api/login nicht erreichbar ist oder einen
    unerwarteten Fehler zurÃ¼ckgibt, werden lokale Test-Zugangsdaten genutzt.
    Nur bei explizitem 401 vom Backend wird der Fallback NICHT aktiviert."""
    username     = request.form.get('username')
    password     = request.form.get('password')
    desired_role = request.form.get('role', 'student')

    # Versuch 1: Login Ã¼ber das Backend (Produktivmodus)
    backend_hat_explizit_abgelehnt = False
    try:
        response = requests.post(f"{BACKEND_API_URL}/login", json={
            "username": username,
            "password": password
        }, timeout=3)

        if response.ok:
            # Backend hat erfolgreich eingeloggt â†’ Token speichern
            data = response.json()
            session['token']    = data.get('token')
            session['role']     = data.get('role', desired_role)
            session['username'] = username
            flash("Erfolgreich eingeloggt.")
            if session['role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('survey', role=session['role']))

        if response.status_code == 401:
            # Backend kennt den Benutzer und lehnt ihn explizit ab â†’ kein Fallback
            backend_hat_explizit_abgelehnt = True

        # Alle anderen Codes (404, 405, 500 etc.) â†’ Fallback auf DEV_TEST_USERS

    except Exception:
        # Backend nicht erreichbar â†’ Fallback
        pass

    # Versuch 2: Lokale Test-Zugangsdaten (Entwicklungsmodus)
    if not backend_hat_explizit_abgelehnt:
        test_user = DEV_TEST_USERS.get(username)
        if test_user and test_user["password"] == password:
            session['token']    = f"dev-token-{username}"
            session['role']     = test_user["role"]
            session['username'] = username
            flash(f"Eingeloggt als {username} (Entwicklungsmodus).")
            if test_user["role"] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('survey', role=test_user["role"]))

    flash("Login fehlgeschlagen. Bitte Ã¼berprÃ¼fen Sie Ihre Zugangsdaten.", "error")
    return redirect(url_for('login_page', role=desired_role))


@app.route('/logout')
def logout():
    """LÃ¶scht das Token aus der Session."""
    session.clear()
    flash("Sie wurden abgemeldet.")
    return redirect(url_for('index'))

# ==============================================================
# Hilfsfunktionen: Umfrage-Validierung (vgl. requirements.md Kap. 11 & 13)
# ==============================================================

def lese_antwort_aus_formular(frage):
    """Liest die Antwort fÃ¼r eine Frage typgerecht aus dem Formular.
    Behandelt Mehrfachauswahl (Checkboxen) korrekt via getlist().
    Speicherformat fÃ¼r multiple_choice: kommaseparierter String (vgl. Kap. 13)."""
    typ = frage.get('type', 'text')
    if typ == 'multiple_choice':
        # Checkbox: mehrere Werte mÃ¶glich â†’ als kommaseparierter String speichern
        werte = request.form.getlist('answer')
        return ','.join(werte)  # z.B. "opt1,opt3"
    else:
        # text, single_choice, rating: genau ein Wert
        return request.form.get('answer', '').strip()

def pruefe_pflichtfeld(frage, antwort):
    """PrÃ¼ft serverseitig, ob eine Pflichtfrage beantwortet wurde.
    Behandelt alle 4 Fragetypen (text, single_choice, multiple_choice, rating).
    Gibt None zurÃ¼ck wenn gÃ¼ltig, sonst eine deutsche Fehlermeldung.
    HTML5-required gilt nur als visuelle Hilfe â€“ nie als Sicherheitsmerkmal!"""
    if not frage.get('required', False):
        return None  # Keine Pflichtfrage â†’ immer gÃ¼ltig
    if not antwort or not antwort.strip():
        typ = frage.get('type', 'text')
        if typ == 'rating':
            return "Bitte geben Sie eine Bewertung (1â€“5 Sterne) ab."
        elif typ in ('single_choice', 'multiple_choice'):
            return "Bitte wÃ¤hlen Sie mindestens eine Option aus."
        return "Bitte beantworten Sie diese Pflichtfrage, bevor Sie fortfahren."
    return None  # Antwort vorhanden â†’ gÃ¼ltig

def pruefe_payload_integritaet(survey_data, answers):
    """PrÃ¼ft, ob alle Pflichtfragen der Umfrage beantwortet wurden.
    Wird vor dem finalen Absenden an das Backend aufgerufen (vgl. Kap. 11).
    Gibt eine Liste fehlender Fragen-IDs zurÃ¼ck (leer = alles in Ordnung)."""
    fehlende = []
    for frage in survey_data.get('questions', []):
        if frage.get('required', False):
            antwort = answers.get(frage['id'], '').strip()
            if not antwort:
                fehlende.append(frage['id'])
    return fehlende

def ist_bereits_teilgenommen(survey_id):
    """PrÃ¼ft den Missbrauchsschutz-Cookie (vgl. requirements.md Kap. 10).
    Gibt True zurÃ¼ck, wenn der Nutzer an dieser Umfrage bereits teilgenommen hat."""
    cookie_name = f"survey_completed_{survey_id}"
    return request.cookies.get(cookie_name) == "true"

def berechne_statistiken(umfragen, ergebnisse):
    """Berechnet AntworthÃ¤ufigkeiten fÃ¼r Multiple-Choice-Fragen aller Umfragen.
    Wird fÃ¼r die HTML/CSS-Balkengrafik in Tab 1 des Admin-Dashboards genutzt
    (vgl. requirements.md Kap. 12.1, Funktion 1.4 â€“ kein JavaScript).

    RÃ¼ckgabe: dict { survey_id: { frage_label: { option_text: anzahl, '_gesamt': n } } }
    """
    statistiken = {}
    for umfrage in umfragen:
        sid = umfrage.get('survey_id', '')
        statistiken[sid] = {}
        # Nur Fragen mit Optionen auswerten (single_choice, multiple_choice, rating)
        for frage in umfrage.get('questions', []):
            if frage.get('type') not in ('single_choice', 'multiple_choice', 'rating'):
                continue
            fid   = frage['id']
            label = frage.get('label', fid)
            # Optionen-Map aufbauen: value â†’ Anzahl
            zaehler = {}
            if frage.get('options'):
                for opt in frage['options']:
                    zaehler[opt['text']] = 0
            else:
                # rating: Optionen 1â€“5
                for i in range(1, 6):
                    zaehler[str(i)] = 0

            gesamt = 0
            for ergebnis in ergebnisse:
                if ergebnis.get('survey_id') != sid:
                    continue
                rohwert = ergebnis.get('answers', {}).get(fid, '')
                if not rohwert:
                    continue
                # multiple_choice: kommasepariert aufsplitten
                einzelwerte = [v.strip() for v in rohwert.split(',')] if ',' in rohwert else [rohwert]
                for wert in einzelwerte:
                    # Wert auf Optionstext mappen
                    angezeigter_text = wert  # Fallback: Rohwert anzeigen
                    if frage.get('options'):
                        for opt in frage['options']:
                            if opt['value'] == wert or opt['text'] == wert:
                                angezeigter_text = opt['text']
                                break
                    zaehler[angezeigter_text] = zaehler.get(angezeigter_text, 0) + 1
                    gesamt += 1

            zaehler['_gesamt'] = gesamt
            statistiken[sid][label] = zaehler
    return statistiken

# ==============================================================
# Routen: Umfrage (mit Route Guarding & Serverseitiger Validierung)
# ==============================================================

@app.route('/', methods=['GET'])
def index():
    """Startseite: Rollenauswahl (Admin, Professor, Student)."""
    return render_template('role_select.html')

@app.route('/survey', methods=['GET'])
def survey():
    """Zeigt eine einzelne Umfrage-Frage an.

    ROUTE GUARDING (vgl. requirements.md Kap. 11):
    Der angefragte Schritt wird gegen den in der Session gespeicherten
    maximalen erlaubten Schritt geprÃ¼ft. Versucht ein Nutzer per URL-
    Manipulation einen noch nicht erreichten Schritt aufzurufen, wird er
    automatisch auf seinen korrekten Schritt zurÃ¼ckgeleitet (HTTP 302).
    """
    role = request.args.get('role', 'student')
    angefragter_step = request.args.get('step', 0, type=int)

    # -------------------------------------------------------
    # Missbrauchsschutz: Teilnahme-Cookie prÃ¼fen (Kap. 10)
    # Nur beim Start einer neuen Umfrage (step=0) prÃ¼fen
    # -------------------------------------------------------
    if angefragter_step == 0:
        # Beim Neustart die bisherige Session der Umfrage lÃ¶schen
        session.pop('survey_data', None)
        session.pop('survey_answers', None)
        session.pop('survey_role', None)
        session.pop('survey_max_step', None)
        session.pop('survey_version_id', None)

    # -------------------------------------------------------
    # Umfragedaten laden und in Session cachen
    # -------------------------------------------------------
    if 'survey_data' not in session or session.get('survey_role') != role:
        try:
            response = requests.get(
                f"{BACKEND_API_URL}/survey?role={role}",
                headers=get_auth_headers()
            )
            if response.status_code == 401:
                session.clear()
                flash("Ihre Sitzung ist abgelaufen. Bitte loggen Sie sich neu ein.")
                return redirect(url_for('login_page', role=role))
            response.raise_for_status()
            survey_data = response.json()

            # Versionskontrolle: survey_id als Versionskennung speichern (Kap. 10)
            session['survey_data']       = survey_data
            session['survey_role']       = role
            session['survey_version_id'] = survey_data.get('survey_id', '')
            session['survey_answers']    = {}
            session['survey_max_step']   = 0  # Maximal erreichter Schritt
        except Exception as e:
            print(f"Fehler beim Abrufen der Umfrage: {e}")
            return render_template('index.html', survey=None, role=role,
                                   question=None, step=0, total=0, fehler=None)

    survey_data = session.get('survey_data')
    if not survey_data:
        return render_template('index.html', survey=None, role=role,
                               question=None, step=0, total=0, fehler=None)

    # -------------------------------------------------------
    # Missbrauchsschutz: Teilnahme-Cookie prÃ¼fen (Kap. 10)
    # Blockiert API-Abruf / Umfrage-Zugriff bei erneutem Aufruf
    # -------------------------------------------------------
    survey_id = survey_data.get('survey_id', '')
    if ist_bereits_teilgenommen(survey_id):
        return render_template('success.html', bereits_teilgenommen=True)

    questions = survey_data.get('questions', [])
    total     = len(questions)

    # -------------------------------------------------------
    # Versionskontrolle: PrÃ¼fen ob die Umfrage zwischenzeitlich
    # verÃ¤ndert wurde (unterschiedliche survey_id â†’ Neustart erzwingen)
    # -------------------------------------------------------
    if session.get('survey_version_id') != survey_data.get('survey_id', ''):
        flash("Die Umfrage wurde aktualisiert. Bitte starten Sie neu.")
        session.pop('survey_data', None)
        return redirect(url_for('survey', role=role, step=0))

    # -------------------------------------------------------
    # Route Guarding: Nur erlaubte Schritte zulassen (Kap. 11)
    # Maximaler erlaubter Schritt = hÃ¶chster bisher gesendeter Schritt
    # -------------------------------------------------------
    max_erlaubter_step = session.get('survey_max_step', 0)

    if angefragter_step < 0:
        angefragter_step = 0

    if angefragter_step > max_erlaubter_step:
        # Manipulation erkannt â†’ still auf korrekten Schritt umleiten
        return redirect(url_for('survey', role=role, step=max_erlaubter_step))

    if angefragter_step >= total:
        angefragter_step = total - 1

    current_question = questions[angefragter_step]
    saved_answer = session.get('survey_answers', {}).get(current_question['id'], '')

    return render_template('index.html',
                           survey=survey_data,
                           question=current_question,
                           saved_answer=saved_answer,
                           step=angefragter_step,
                           total=total,
                           role=role,
                           fehler=None)  # Kein Fehler beim normalen Laden


@app.route('/survey/next', methods=['POST'])
def survey_next():
    """Verarbeitet den Formular-Submit einer einzelnen Frage.

    SERVERSEITIGE PFLICHTFELD-PRÃœFUNG (vgl. requirements.md Kap. 11):
    Jede Antwort wird gegen die Originaldefinition der Umfrage validiert.
    Bei Fehler â†’ Seite neu rendern mit Fehlermeldung (kein Redirect).

    ROUTE GUARDING:
    survey_max_step wird nur erhÃ¶ht, wenn die Validierung erfolgreich war.
    """
    role        = request.form.get('role', 'student')
    step        = request.form.get('step', 0, type=int)
    question_id = request.form.get('question_id', '')
    # Typgerechte Antwort lesen: multiple_choice via getlist(), Rest via get()
    # (vgl. lese_antwort_aus_formular â€“ Kap. 13 Zustandsdefinition)
    aktuelle_frage_vorab = None
    survey_data_vorab = session.get('survey_data')
    if survey_data_vorab:
        fragen_vorab = survey_data_vorab.get('questions', [])
        step_vorab = request.form.get('step', 0, type=int)
        if 0 <= step_vorab < len(fragen_vorab):
            aktuelle_frage_vorab = fragen_vorab[step_vorab]
    if aktuelle_frage_vorab:
        answer = lese_antwort_aus_formular(aktuelle_frage_vorab)
    else:
        answer = request.form.get('answer', '').strip()

    survey_data = session.get('survey_data')
    if not survey_data:
        flash("Sitzung abgelaufen. Bitte starten Sie die Umfrage erneut.")
        return redirect(url_for('index'))

    questions = survey_data.get('questions', [])
    total     = len(questions)

    # -------------------------------------------------------
    # Die aktuelle Frage aus der Originaldefinition ermitteln
    # -------------------------------------------------------
    if step < 0 or step >= total:
        return redirect(url_for('survey', role=role, step=0))

    aktuelle_frage = questions[step]

    # -------------------------------------------------------
    # Serverseitige Pflichtfeld-PrÃ¼fung (Kap. 11)
    # HTML5-required ist nur visuelle Hilfe â€“ wir erzwingen es hier!
    # -------------------------------------------------------
    fehler = pruefe_pflichtfeld(aktuelle_frage, answer)
    if fehler:
        # Fehler: Aktuelle Seite mit Fehlermeldung neu rendern (kein Redirect)
        saved_answer = session.get('survey_answers', {}).get(question_id, answer)
        return render_template('index.html',
                               survey=survey_data,
                               question=aktuelle_frage,
                               saved_answer=saved_answer,
                               step=step,
                               total=total,
                               role=role,
                               fehler=fehler), 422

    # -------------------------------------------------------
    # Validierung erfolgreich: Antwort in Session speichern
    # -------------------------------------------------------
    answers = session.get('survey_answers', {})
    answers[question_id] = answer
    session['survey_answers'] = answers

    # Maximalen erlaubten Schritt erhÃ¶hen (Route Guarding)
    naechster_step = step + 1
    session['survey_max_step'] = max(session.get('survey_max_step', 0), naechster_step)

    # -------------------------------------------------------
    # Letzte Frage beantwortet â†’ Payload-IntegritÃ¤t prÃ¼fen & Absenden
    # -------------------------------------------------------
    if naechster_step >= total:
        return redirect(url_for('survey_submit'))

    return redirect(url_for('survey', role=role, step=naechster_step))


@app.route('/survey/back', methods=['POST'])
def survey_back():
    """Geht eine Frage zurÃ¼ck. Speichert die aktuelle Antwort ohne Validierung
    (Pflichtfeld-PrÃ¼fung gilt nur beim VorwÃ¤rtsgehen, nie beim ZurÃ¼ckgehen)."""
    role        = request.form.get('role', 'student')
    step        = request.form.get('step', 0, type=int)
    question_id = request.form.get('question_id', '')
    answer      = request.form.get('answer', '').strip()

    # Antwort auch beim ZurÃ¼ckgehen speichern (falls bereits ausgefÃ¼llt)
    if answer:
        answers = session.get('survey_answers', {})
        answers[question_id] = answer
        session['survey_answers'] = answers

    prev_step = max(0, step - 1)
    return redirect(url_for('survey', role=role, step=prev_step))


@app.route('/survey/submit', methods=['GET'])
def survey_submit():
    """Finaler Abschluss der Umfrage.

    PAYLOAD-INTEGRITÃ„T (vgl. requirements.md Kap. 11):
    Vor dem Senden an das Backend wird geprÃ¼ft, ob alle Pflichtfragen
    beantwortet wurden. Fehlt eine Antwort, wird der Nutzer zur ersten
    unbeantworteten Frage zurÃ¼ckgeleitet.

    MISSBRAUCHSSCHUTZ (vgl. requirements.md Kap. 10):
    Nach erfolgreichem Absenden wird ein Cookie gesetzt, der eine
    erneute Teilnahme fÃ¼r 30 Tage blockiert (Frictionless Security).
    """
    survey_data = session.get('survey_data')
    answers     = session.get('survey_answers', {})
    role        = session.get('survey_role', 'student')

    if not survey_data:
        flash("Keine Umfragedaten gefunden. Bitte starten Sie erneut.")
        return redirect(url_for('index'))

    # -------------------------------------------------------
    # Payload-IntegritÃ¤t prÃ¼fen: Alle Pflichtfelder beantwortet?
    # -------------------------------------------------------
    fehlende_fragen = pruefe_payload_integritaet(survey_data, answers)
    if fehlende_fragen:
        # Zur ersten unbeantworteten Pflichtfrage zurÃ¼ckleiten
        questions = survey_data.get('questions', [])
        fragen_ids = [f['id'] for f in questions]
        erste_fehlende_idx = 0
        for idx, fid in enumerate(fragen_ids):
            if fid in fehlende_fragen:
                erste_fehlende_idx = idx
                break

        flash(f"Bitte beantworten Sie alle Pflichtfragen. "
              f"{len(fehlende_fragen)} Pflichtfrage(n) fehlen noch.")
        # survey_max_step zurÃ¼cksetzen, damit der Nutzer wieder vorankommen kann
        session['survey_max_step'] = erste_fehlende_idx
        return redirect(url_for('survey', role=role, step=erste_fehlende_idx))

    # -------------------------------------------------------
    # Finaler Payload an das Backend senden
    # -------------------------------------------------------
    survey_id = survey_data.get('survey_id', 'unknown')
    payload = {
        "survey_id": survey_id,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "answers":   answers
    }

    try:
        requests.post(
            f"{BACKEND_API_URL}/results",
            json=payload,
            headers=get_auth_headers()
        )
    except Exception as e:
        print(f"Warnung: Fehler beim Senden der Ergebnisse ({e}).")

    # -------------------------------------------------------
    # Session-Daten der abgeschlossenen Umfrage bereinigen
    # -------------------------------------------------------
    session.pop('survey_data', None)
    session.pop('survey_answers', None)
    session.pop('survey_role', None)
    session.pop('survey_max_step', None)
    session.pop('survey_version_id', None)

    # -------------------------------------------------------
    # Missbrauchsschutz-Cookie setzen (30 Tage, vgl. Kap. 10)
    # survey_completed_<survey_id>=true verhindert erneute Teilnahme
    # -------------------------------------------------------
    antwort = render_template('success.html')
    response = app.make_response(antwort)
    response.set_cookie(
        key=f"survey_completed_{survey_id}",
        value="true",
        max_age=30 * 24 * 60 * 60,  # 30 Tage in Sekunden
        httponly=True,               # Nicht per JavaScript auslesbar
        samesite='Lax'
    )
    return response

# ==============================================================
# Routen: Admin Dashboard & Verwaltung
# ==============================================================

# Pfad zum Backend-Datenverzeichnis (fÃ¼r direkten Dateizugriff als Fallback)
import pathlib
BACKEND_DATEN_PFAD = pathlib.Path(__file__).parent.parent / "backend" / "data"

def lade_alle_umfragen_lokal():
    """LÃ¤dt alle bekannten Umfrage-Dateien direkt aus dem Backend-Datenverzeichnis.
    Dient als zuverlÃ¤ssiger Fallback, wenn der Backend-API-Endpunkt noch nicht implementiert ist."""
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
                    daten["_rolle"] = rolle       # Interne Rolle fÃ¼r die Anzeige ergÃ¤nzen
                    daten["_datei"] = dateiname   # Dateiname fÃ¼r Debugging-Zwecke
                    umfragen.append(daten)
            except Exception as e:
                print(f"Warnung: Konnte {dateiname} nicht laden: {e}")
    return umfragen

def lade_ergebnisse():
    """Versucht Ergebnisse vom Backend (im CSV-Format) zu laden und zu parsen.
    FÃ¤llt bei Fehlern auf direktes Lesen der lokalen CSV-Dateien aus backend/data/ zurÃ¼ck."""
    import csv
    import io
    # Versuch 1: Backend-API GET /api/results
    try:
        import time
        t = int(time.time())
        res = requests.get(f"{BACKEND_API_URL}/results?t={t}", headers=get_auth_headers(), timeout=2)
        if res.status_code == 401:
            raise PermissionError("Sitzung abgelaufen")
        if res.ok:
            csv_data = res.text
            if csv_data.startswith('\ufeff'):
                csv_data = csv_data[1:]

            f = io.StringIO(csv_data)
            reader = csv.reader(f, delimiter=';')
            try:
                next(reader)  # Header Ã¼berspringen
            except StopIteration:
                return []

            ergebnisse_dict = {}
            for row in reader:
                if len(row) < 5:
                    continue
                result_id, timestamp, survey_id, question_id, answer = row
                if result_id not in ergebnisse_dict:
                    ergebnisse_dict[result_id] = {
                        "result_id": result_id,
                        "received_at": timestamp,
                        "survey_id": survey_id,
                        "answers": {}
                    }
                ergebnisse_dict[result_id]["answers"][question_id] = answer
            return list(ergebnisse_dict.values())
    except PermissionError:
        raise
    except Exception as e:
        print(f"Fehler beim Laden/Parsen der API-Ergebnisse: {e}")

    # Versuch 2: Direkt aus dem Ergebnis-Verzeichnis / CSV-Dateien lesen (Entwicklungsmodus Fallback)
    import glob
    ergebnisse_dict = {}
    try:
        csv_dateien = glob.glob(str(BACKEND_DATEN_PFAD / "results_*.csv"))
        for datei_pfad in csv_dateien:
            with open(datei_pfad, "r", encoding="utf-8") as f:
                csv_data = f.read()
                if csv_data.startswith('\ufeff'):
                    csv_data = csv_data[1:]
                reader = csv.reader(io.StringIO(csv_data), delimiter=';')
                try:
                    next(reader)  # Header Ã¼berspringen
                except StopIteration:
                    continue
                for row in reader:
                    if len(row) < 5:
                        continue
                    result_id, timestamp, survey_id, question_id, answer = row
                    if result_id not in ergebnisse_dict:
                        ergebnisse_dict[result_id] = {
                            "result_id": result_id,
                            "received_at": timestamp,
                            "survey_id": survey_id,
                            "answers": {}
                        }
                    ergebnisse_dict[result_id]["answers"][question_id] = answer
    except Exception as e:
        print(f"Fallback-Fehler beim Lesen der CSVs: {e}")

    return list(ergebnisse_dict.values())

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    """Admin-Dashboard: LÃ¤dt alle Umfragen, Ergebnisse und Statistiken fÃ¼r die 3-Tab-Ansicht.
    Statistiken werden serverseitig berechnet fÃ¼r die HTML/CSS-Balkengrafik (Kap. 12.1 Funktion 1.4)."""
    try:
        alle_ergebnisse = lade_ergebnisse()
    except PermissionError:
        session.clear()
        flash("Ihre Sitzung ist abgelaufen. Bitte loggen Sie sich neu ein.")
        return redirect(url_for('login_page'))

    alle_umfragen = lade_alle_umfragen_lokal()
    # Antwortstatistiken fÃ¼r Balkengrafik serverseitig berechnen (kein JS, vgl. Kap. 12.4)
    alle_statistiken = berechne_statistiken(alle_umfragen, alle_ergebnisse)
    resp = make_response(render_template('admin.html',
                                         umfragen=alle_umfragen,
                                         ergebnisse=alle_ergebnisse,
                                         statistiken=alle_statistiken))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

@app.route('/admin/results/export', methods=['GET'])
@login_required
def admin_results_export():
    """CSV-Export aller Umfrageergebnisse (vgl. requirements.md Kap. 12.1, Funktion 1.5).

    Zustandsdefinition (Kap. 13):
    - Kein Session-Zustand: Export wird bei jedem Aufruf frisch generiert (zustandslos)
    - Liest Ergebnisse aus backend/data/results/*.json oder via API
    - UI-Zustand: Browser-Download-Dialog (Content-Disposition: attachment)
    - Fehlerzustand: Keine Daten â†’ leere CSV mit Header-Zeile (kein Fehler, kein 4xx)
    """
    import io
    import csv
    from flask import Response

    alle_ergebnisse = lade_ergebnisse()

    # CSV im Arbeitsspeicher aufbauen (kein temporÃ¤res File auf der Festplatte)
    ausgabe = io.StringIO()
    schreiber = csv.writer(ausgabe, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)

    # Kopfzeile
    schreiber.writerow(['Ergebnis-ID', 'Zeitstempel', 'Umfrage-ID', 'Frage-ID', 'Antwort'])

    survey_id_filter = request.args.get('survey_id')

    for ergebnis in alle_ergebnisse:
        eid       = ergebnis.get('result_id', ergebnis.get('id', 'â€“'))
        zeitpunkt = ergebnis.get('received_at', ergebnis.get('timestamp', 'â€“'))
        sid       = ergebnis.get('survey_id', 'â€“')
        if survey_id_filter and sid != survey_id_filter:
            continue
        for frage_id, antwort in ergebnis.get('answers', {}).items():
            schreiber.writerow([eid, zeitpunkt, sid, frage_id, antwort])

    # UTF-8 mit BOM fÃ¼r korrekte Darstellung in Excel (Ã¼, Ã¤, Ã¶)
    csv_inhalt = '\ufeff' + ausgabe.getvalue()

    dateiname = f"umfrage_ergebnisse_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_inhalt,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{dateiname}"'}
    )

@app.route('/api/survey', methods=['GET'])
@login_required
def api_get_survey():
    """Proxy-Route zum Laden der JSON-Struktur einer Umfrage."""
    import json as json_mod
    role = request.args.get('role', 'student')
    survey_id = request.args.get('survey_id', '')

    # Wenn survey_id Ã¼bergeben wurde, bestimmen wir die Rolle
    if survey_id:
        if 'student' in survey_id.lower():
            role = 'student'
        elif 'professor' in survey_id.lower():
            role = 'professor'

    # Vom Backend abrufen
    try:
        response = requests.get(
            f"{BACKEND_API_URL}/survey?role={role}",
            headers=get_auth_headers(),
            timeout=2
        )
        if response.status_code == 401:
            session.clear()
            return json_mod.dumps({"status": "error", "message": "Sitzung abgelaufen."}), 401, {"Content-Type": "application/json"}
        if response.ok:
            return response.text, 200, {"Content-Type": "application/json"}
    except Exception:
        pass

    # Lokaler Fallback
    try:
        dateiname = f"survey_{role}.json"
        with open(BACKEND_DATEN_PFAD / dateiname, "r", encoding="utf-8") as f:
            return f.read(), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": str(e)}), 500, {"Content-Type": "application/json"}

@app.route('/admin/surveys/save', methods=['POST'])
@login_required
def survey_save_local():
    """Speichert eine Umfrage. Ruft den API-Endpunkt POST /api/surveys auf.
    FÃ¤llt bei Verbindungsfehlern auf lokales Speichern zurÃ¼ck (Entwicklungsmodus)."""
    import json as json_mod

    nutzlast = request.get_json(silent=True)
    if not nutzlast:
        return json_mod.dumps({"status": "error", "message": "Kein gÃ¼ltiger JSON-Body empfangen."}), 400, {"Content-Type": "application/json"}

    rolle = nutzlast.get("role", "")
    if rolle not in ["student", "professor"]:
        return json_mod.dumps({"status": "error", "message": "Feld 'role' muss 'student' oder 'professor' sein."}), 400, {"Content-Type": "application/json"}

    dateiname = f"survey_{rolle}.json"
    ziel_pfad = BACKEND_DATEN_PFAD / dateiname

    # Versuch 1: Echten Backend-Endpunkt POST /api/surveys nutzen
    try:
        antwort = requests.post(
            f"{BACKEND_API_URL}/surveys",
            json=nutzlast,
            headers={**get_auth_headers(), "Content-Type": "application/json"},
            timeout=2
        )
        # Wenn Token abgelaufen (401), Session verwerfen und an Login weiterleiten
        if antwort.status_code == 401:
            session.clear()
            return json_mod.dumps({"status": "error", "message": "Sitzung abgelaufen. Bitte neu anmelden."}), 401, {"Content-Type": "application/json"}
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

@app.route('/admin/surveys/delete/<survey_id>', methods=['POST'])
@login_required
def survey_delete(survey_id):
    """Proxy-Route zum LÃ¶schen einer Umfrage via Backend-API DELETE /api/surveys/{survey_id}."""
    import json as json_mod

    # Versuch 1: Echten Backend-Endpunkt nutzen
    try:
        antwort = requests.delete(
            f"{BACKEND_API_URL}/surveys/{survey_id}",
            headers=get_auth_headers(),
            timeout=2
        )
        if antwort.status_code == 401:
            session.clear()
            return json_mod.dumps({"status": "error", "message": "Sitzung abgelaufen. Bitte neu anmelden."}), 401, {"Content-Type": "application/json"}
        if antwort.status_code == 204:
            return json_mod.dumps({"status": "deleted"}), 200, {"Content-Type": "application/json"}
    except Exception:
        pass

    # Versuch 2: Direkt aus dem Dateisystem lÃ¶schen (Entwicklungsmodus Fallback)
    rolle = "student" if "student" in survey_id.lower() else "professor"
    dateiname = f"survey_{rolle}.json"
    ziel_pfad = BACKEND_DATEN_PFAD / dateiname
    try:
        if ziel_pfad.exists():
            ziel_pfad.unlink()
            return json_mod.dumps({"status": "deleted", "message": f"Datei {dateiname} gelÃ¶scht"}), 200, {"Content-Type": "application/json"}
        return json_mod.dumps({"status": "error", "message": "Umfrage-Datei existiert nicht."}), 404, {"Content-Type": "application/json"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": f"Fehler beim LÃ¶schen: {e}"}), 500, {"Content-Type": "application/json"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
