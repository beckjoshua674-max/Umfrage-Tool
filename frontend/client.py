# Ask Alma - Umfrage-Tool Frontend
# Website: http://127.0.0.1:5000/

import os
import json
import datetime
import requests
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
import pathlib


# Versuche .env-Datei einzulesen, falls vorhanden
env_pfad = pathlib.Path(__file__).resolve().parent / ".env"
if env_pfad.exists():
    try:
        with env_pfad.open("r", encoding="utf-8") as env_file:
            for zeile in env_file:
                zeile = zeile.strip()
                if zeile and not zeile.startswith("#") and "=" in zeile:
                    k, v = zeile.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        print(f"Fehler beim Laden der .env Datei im Frontend: {e}")

app = Flask(__name__)
app.secret_key = os.environ.get("ASK_ALMA_CLIENT_SECRET", "ask-alma-secret-key-dev")
app.json.ensure_ascii = False
app.config['JSON_AS_ASCII'] = False


@app.before_request
def auto_logout_admin_on_leave():
    """Löscht die Session automatisch, wenn ein Admin die Admin-Ansicht verlässt."""
    if session.get('role') == 'admin':
        pfad = request.path
        # Wenn der Pfad nicht mit /admin beginnt und auch nicht /logout, /static oder /favicon.ico ist,
        # wird die Session gelöscht (automatischer Logout bei URL-Wechsel).
        if not pfad.startswith('/admin') and not pfad.startswith('/api') and pfad not in ['/logout', '/favicon.ico'] and not pfad.startswith('/static'):
            session.clear()
            flash("Ihre Administrator-Sitzung wurde beim Verlassen der Admin-Ansicht automatisch beendet.")


# Konfiguration: URL des echten Backends (wird später von Codex bereitgestellt)
BACKEND_API_URL = "http://localhost:8000/api"
DEV_MODE = os.environ.get("ASK_ALMA_DEV_MODE", "false").lower() == "true"

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
    """Sendet Credentials an Backend und speichert JWT Token in der Session.
    Fallback: Wenn das Backend /api/login nicht erreichbar ist oder einen
    unerwarteten Fehler zurückgibt, werden lokale Test-Zugangsdaten genutzt.
    Nur bei explizitem 401 vom Backend wird der Fallback NICHT aktiviert."""
    username     = request.form.get('username')
    password     = request.form.get('password')
    desired_role = request.form.get('role', 'student')

    try:
        response = requests.post(f"{BACKEND_API_URL}/login", json={
            "username": username,
            "password": password
        }, timeout=3)

        if response.ok:
            data = response.json()
            session['token']    = data.get('token')
            session['role']     = data.get('role', desired_role)
            session['username'] = username
            flash("Erfolgreich eingeloggt.")
            if session['role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('survey', role=session['role']))
    except Exception:
        pass

    flash("Login fehlgeschlagen. Bitte überprüfen Sie Ihre Zugangsdaten.", "error")
    return redirect(url_for('login_page', role=desired_role))


@app.route('/logout')
def logout():
    """Löscht das Token aus der Session."""
    session.clear()
    flash("Sie wurden abgemeldet.")
    return redirect(url_for('index'))

# ==============================================================
# Hilfsfunktionen: Umfrage-Validierung (vgl. requirements.md Kap. 11 & 13)
# ==============================================================

def antwort_ist_leer(antwort):
    """Prueft leere Antworten typunabhaengig."""
    if antwort is None:
        return True
    if isinstance(antwort, list):
        return not any(str(wert).strip() for wert in antwort)
    return str(antwort).strip() == ""


def normalisiere_antwortwerte(antwort):
    """Normalisiert Antworten fuer Auswertung und Anzeige zu einer Werteliste."""
    if antwort is None:
        return []
    if isinstance(antwort, list):
        return [str(wert).strip() for wert in antwort if str(wert).strip()]
    text = str(antwort).strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        text = text[1:-1].strip()
    if not text:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            werte = json.loads(text.replace("'", '"'))
            if isinstance(werte, list):
                return [str(wert).strip() for wert in werte if str(wert).strip()]
        except Exception:
            # Manueller Fallback fuer nicht-JSON-konforme Listen (z.B. mit einfachen Anfuehrungszeichen)
            innen = text[1:-1].strip()
            if innen:
                teile = [t.strip().strip("'").strip('"') for t in innen.split(",")]
                return [t for t in teile if t]
            return []
    return [text]


def zerlege_legacy_werte(text, erlaubte_werte):
    """Rekonstruiert alte kommagetrennte Antworten anhand erlaubter Werte."""
    teile = [teil.strip() for teil in text.split(',')]
    werte = []
    index = 0
    while index < len(teile):
        treffer = None
        treffer_ende = index + 1
        for ende in range(len(teile), index, -1):
            kandidat = ','.join(teile[index:ende]).strip()
            if kandidat in erlaubte_werte:
                treffer = kandidat
                treffer_ende = ende
                break
        if treffer is None:
            return [wert.strip() for wert in text.split(',') if wert.strip()]
        werte.append(treffer)
        index = treffer_ende
    return werte


def normalisiere_multiple_choice_sessionwert(antwort, option_values):
    """Normalisiert gespeicherte Multiple-Choice-Werte fuer erneutes Rendering."""
    if isinstance(antwort, list):
        return normalisiere_antwortwerte(antwort)
    if isinstance(antwort, str):
        text = antwort.strip()
        if not text:
            return []
        if text in option_values:
            return [text]
        werte = normalisiere_antwortwerte(text)
        if len(werte) == 1 and ',' in werte[0]:
            legacy_werte = zerlege_legacy_werte(werte[0], option_values)
            if all(wert in option_values for wert in legacy_werte):
                return legacy_werte
        return werte
    return []


def parse_csv_antwort(antwort):
    """Liest JSON-Array-Antworten aus CSV-Feldern wieder als Liste."""
    werte = normalisiere_antwortwerte(antwort)
    if isinstance(antwort, str) and antwort.strip().startswith("[") and antwort.strip().endswith("]"):
        return werte
    return antwort


def formatiere_export_antwort(antwort):
    """Serialisiert Listenantworten eindeutig fuer CSV-Exports."""
    if isinstance(antwort, list):
        return json.dumps(normalisiere_antwortwerte(antwort), ensure_ascii=False, separators=(",", ":"))
    return antwort


def lese_antwort_aus_formular(frage):
    """Liest die Antwort für eine Frage typgerecht aus dem Formular.
    Behandelt Mehrfachauswahl (Checkboxen) korrekt via getlist().
    Speicherformat für multiple_choice: Liste von Option-Values (vgl. Kap. 13)."""
    typ = frage.get('type', 'text')
    if typ == 'multiple_choice':
        # Checkbox: mehrere Werte moeglich. Als Liste bleiben Kommata in Optionswerten erhalten.
        return [wert.strip() for wert in request.form.getlist('answer') if wert.strip()]
    else:
        # text, single_choice, rating: genau ein Wert
        return request.form.get('answer', '').strip()

def pruefe_pflichtfeld(frage, antwort):
    """Prüft serverseitig, ob eine Pflichtfrage beantwortet wurde.
    Behandelt alle 4 Fragetypen (text, single_choice, multiple_choice, rating).
    Gibt None zurück wenn gültig, sonst eine deutsche Fehlermeldung.
    HTML5-required gilt nur als visuelle Hilfe â€“ nie als Sicherheitsmerkmal!"""
    if not frage.get('required', False):
        return None  # Keine Pflichtfrage â†’ immer gültig
    if antwort_ist_leer(antwort):
        typ = frage.get('type', 'text')
        if typ == 'rating':
            return "Bitte geben Sie eine Bewertung (1â€“5 Sterne) ab."
        elif typ in ('single_choice', 'multiple_choice'):
            return "Bitte wählen Sie mindestens eine Option aus."
        return "Bitte beantworten Sie diese Pflichtfrage, bevor Sie fortfahren."
    return None  # Antwort vorhanden â†’ gültig

def pruefe_payload_integritaet(survey_data, answers):
    """Prüft, ob alle Pflichtfragen der Umfrage beantwortet wurden.
    Wird vor dem finalen Absenden an das Backend aufgerufen (vgl. Kap. 11).
    Gibt eine Liste fehlender Fragen-IDs zurück (leer = alles in Ordnung)."""
    fehlende = []
    for frage in survey_data.get('questions', []):
        if frage.get('required', False):
            antwort = answers.get(frage['id'], '')
            if antwort_ist_leer(antwort):
                fehlende.append(frage['id'])
    return fehlende

def ist_bereits_teilgenommen(survey_id):
    """Prüft den Missbrauchsschutz-Cookie (vgl. requirements.md Kap. 10).
    Gibt True zurück, wenn der Nutzer an dieser Umfrage bereits teilgenommen hat."""
    cookie_name = f"survey_completed_{survey_id}"
    return request.cookies.get(cookie_name) == "saved"

def berechne_statistiken(umfragen, ergebnisse):
    """Berechnet Antworthäufigkeiten für Multiple-Choice-Fragen aller Umfragen.
    Wird für die HTML/CSS-Balkengrafik in Tab 1 des Admin-Dashboards genutzt
    (vgl. requirements.md Kap. 12.1, Funktion 1.4 â€“ kein JavaScript).

    Rückgabe: dict { survey_id: { frage_label: { option_text: anzahl, '_gesamt': n } } }
    """
    statistiken = {}
    for umfrage in umfragen:
        sid = umfrage.get('survey_id', '')
        statistiken[sid] = {}
        for frage in umfrage.get('questions', []):
            fid   = frage['id']
            label = frage.get('label', fid)
            typ   = frage.get('type', 'text')

            if typ not in ('single_choice', 'multiple_choice', 'rating', 'text', 'yes_no', 'date'):
                continue

            if typ in ('text', 'date'):
                antworten = []
                for ergebnis in ergebnisse:
                    if ergebnis.get('survey_id') != sid:
                        continue
                    answers = ergebnis.get('answers', {})
                    rohwert = answers.get(fid)
                    if rohwert is None:
                        # Legacy-Kompatibilität
                        if fid.startswith('q'):
                            alt_fid = 'p' + fid[1:]
                            rohwert = answers.get(alt_fid)
                        elif fid.startswith('p'):
                            alt_fid = 'q' + fid[1:]
                            rohwert = answers.get(alt_fid)
                    if rohwert is not None and str(rohwert).strip():
                        antworten.append(str(rohwert).strip())
                statistiken[sid][label] = {
                    '_typ': 'text',
                    '_antworten': antworten
                }
                continue

            # Optionen-Map aufbauen: value -> Anzahl
            zaehler = {}
            if typ == 'yes_no':
                zaehler['Ja'] = 0
                zaehler['Nein'] = 0
            elif frage.get('options'):
                for opt in frage['options']:
                    zaehler[opt['text']] = 0
            else:
                # rating: Optionen 1-5
                for i in range(1, 6):
                    zaehler[str(i)] = 0

            gesamt = 0
            for ergebnis in ergebnisse:
                if ergebnis.get('survey_id') != sid:
                    continue
                answers = ergebnis.get('answers', {})
                rohwert = answers.get(fid)
                if rohwert is None:
                    # Alternativer Key (z.B. p1 statt q1) für Legacy-Kompatibilität
                    if fid.startswith('q'):
                        alt_fid = 'p' + fid[1:]
                        rohwert = answers.get(alt_fid)
                    elif fid.startswith('p'):
                        alt_fid = 'q' + fid[1:]
                        rohwert = answers.get(alt_fid)
                if rohwert is None or antwort_ist_leer(rohwert):
                    continue
                if frage.get('type') == 'multiple_choice':
                    einzelwerte = normalisiere_antwortwerte(rohwert)
                    erlaubte_werte = {option['value'] for option in frage.get('options', [])}
                    if (
                        isinstance(rohwert, str)
                        and len(einzelwerte) == 1
                        and einzelwerte[0] not in erlaubte_werte
                        and ',' in einzelwerte[0]
                    ):
                        legacy_werte = zerlege_legacy_werte(einzelwerte[0], erlaubte_werte)
                        if all(wert in erlaubte_werte for wert in legacy_werte):
                            einzelwerte = legacy_werte
                else:
                    einzelwerte = [str(rohwert).strip()]
                for wert in einzelwerte:
                    sicherer_wert = str(wert).strip()
                    # Mapping alter Antwortwerte der Professoren-Evaluation auf neue Werte
                    LEGACY_MAPPING = {
                        "kein_nutzen": "opt3_kein_merklicher_nutz",
                        "sehr_hoher_nutzen": "opt1_sehr_hoher_nutzen",
                        "moderater_nutzen": "opt2_moderater_nutzen",
                        "teilweise_entlastet": "opt2_ja__teilweise",
                        "stark_entlastet": "opt1_ja__stark_entlastet",
                        "kaum": "opt3_nein__kaum",
                        "oft_fehlerhaft": "opt3_oft_fehlerhaft",
                        "stets_korrekt": "opt1_stets_korrekt",
                        "meistens_korrekt": "opt2_meistens_korrekt",
                        "vielleicht": "opt2_eventuell",
                        "ja_auf_jeden_fall": "opt1_ja__auf_jeden_fall",
                        "wahrscheinlich_nicht": "opt3_wahrscheinlich_nicht",
                        "gering": "opt3_geringe_akzeptanz",
                        "sehr_hoch": "opt1_sehr_hohe_akzeptanz",
                        "mittlere": "opt2_mittlere_akzeptanz",
                        "nein": "opt3_nein__nicht_n_tig",
                        "ja_dringend": "opt1_ja__dringend",
                        "waere_nett": "opt2_w_re_ein_nettes_feat",
                    }
                    if sicherer_wert in LEGACY_MAPPING:
                        sicherer_wert = LEGACY_MAPPING[sicherer_wert]
                    # Wert auf Optionstext mappen
                    angezeigter_text = sicherer_wert  # Fallback
                    if typ == 'yes_no':
                        if sicherer_wert.lower() == 'ja':
                            angezeigter_text = 'Ja'
                        elif sicherer_wert.lower() == 'nein':
                            angezeigter_text = 'Nein'
                    elif frage.get('options'):
                        for opt in frage['options']:
                            if opt['value'] == sicherer_wert or opt['text'] == sicherer_wert:
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

@app.route('/link/<link_id>', methods=['GET'])
def use_link(link_id):
    """Speichert das Token in der Session und leitet zur Startseite weiter."""
    session['link_id'] = link_id
    return redirect(url_for('index'))

@app.route('/', methods=['GET'])
def index():
    """Startseite: Rollenauswahl und Liste der verfügbaren Umfragen."""
    umfragen = lade_alle_umfragen()
    link_id = session.get('link_id')
    
    if link_id:
        try:
            import requests
            res = requests.get(f"{BACKEND_API_URL}/links", timeout=2)
            if res.ok:
                links = res.json()
                erlaubte_surveys = links.get(link_id)
                if erlaubte_surveys is not None:
                    umfragen = [u for u in umfragen if u.get('survey_id') in erlaubte_surveys]
        except Exception as e:
            print(f"Fehler beim Abrufen der Links: {e}")
            
    return render_template('role_select.html', umfragen=umfragen)

@app.route('/survey', methods=['GET'])
def survey():
    """Zeigt eine einzelne Umfrage-Frage an.

    ROUTE GUARDING (vgl. requirements.md Kap. 11):
    Der angefragte Schritt wird gegen den in der Session gespeicherten
    maximalen erlaubten Schritt geprüft. Versucht ein Nutzer per URL-
    Manipulation einen noch nicht erreichten Schritt aufzurufen, wird er
    automatisch auf seinen korrekten Schritt zurückgeleitet (HTTP 302).
    """
    role = 'student'
    survey_id = request.args.get('survey_id', '')
    angefragter_step = request.args.get('step', 0, type=int)

    # -------------------------------------------------------
    # Missbrauchsschutz: Teilnahme-Cookie prüfen (Kap. 10)
    # Nur beim Start einer neuen Umfrage (step=0) prüfen
    # -------------------------------------------------------
    if angefragter_step == 0:
        # Beim Neustart die bisherige Session der Umfrage löschen
        session.pop('survey_data', None)
        session.pop('survey_answers', None)
        session.pop('survey_role', None)
        session.pop('survey_max_step', None)
        session.pop('survey_version_id', None)

    # -------------------------------------------------------
    # Umfragedaten laden und in Session cachen
    # -------------------------------------------------------
    if 'survey_data' not in session or (survey_id and session.get('survey_version_id') != survey_id):
        try:
            if survey_id:
                url = f"{BACKEND_API_URL}/surveys/{survey_id}"
            else:
                # Get the first survey from the list if no id is provided
                url = f"{BACKEND_API_URL}/surveys"
            response = requests.get(
                url,
                headers=get_auth_headers()
            )
            if response.status_code == 401:
                session.clear()
                flash("Ihre Sitzung ist abgelaufen. Bitte loggen Sie sich neu ein.")
                return redirect(url_for('login_page', role='admin'))
            response.raise_for_status()
            survey_data = response.json()
            if isinstance(survey_data, list):
                if survey_data:
                    survey_data = survey_data[0]
                else:
                    survey_data = None

            # Versionskontrolle: survey_id als Versionskennung speichern (Kap. 10)
            session['survey_data']       = survey_data
            session['survey_role']       = 'student'
            session['survey_version_id'] = survey_data.get('survey_id', '')
            session['survey_answers']    = {}
            session['survey_max_step']   = 0  # Maximal erreichter Schritt
        except Exception as e:
            print(f"Fehler beim Abrufen der Umfrage: {e}")
            return render_template('index.html', survey=None, role='student',
                                   question=None, step=0, total=0, fehler=None)

    survey_data = session.get('survey_data')
    if not survey_data:
        return render_template('index.html', survey=None, role='student',
                               question=None, step=0, total=0, fehler=None)

    # -------------------------------------------------------
    # Missbrauchsschutz: Teilnahme-Cookie prüfen (Kap. 10)
    # Blockiert API-Abruf / Umfrage-Zugriff bei erneutem Aufruf
    # -------------------------------------------------------
    survey_id = survey_data.get('survey_id', '')
    if ist_bereits_teilgenommen(survey_id):
        return render_template('success.html', bereits_teilgenommen=True)

    questions = survey_data.get('questions', [])
    total     = len(questions)

    # -------------------------------------------------------
    # Versionskontrolle: Prüfen ob die Umfrage zwischenzeitlich
    # verändert wurde (unterschiedliche survey_id â†’ Neustart erzwingen)
    # -------------------------------------------------------
    if session.get('survey_version_id') != survey_data.get('survey_id', ''):
        flash("Die Umfrage wurde aktualisiert. Bitte starten Sie neu.")
        session.pop('survey_data', None)
        return redirect(url_for('survey', role=role, step=0))

    # -------------------------------------------------------
    # Route Guarding: Nur erlaubte Schritte zulassen (Kap. 11)
    # Maximaler erlaubter Schritt = höchster bisher gesendeter Schritt
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
    if current_question.get('type') == 'multiple_choice':
        option_values = {option['value'] for option in current_question.get('options', [])}
        saved_answer = normalisiere_multiple_choice_sessionwert(saved_answer, option_values)

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

    SERVERSEITIGE PFLICHTFELD-PRÜFUNG (vgl. requirements.md Kap. 11):
    Jede Antwort wird gegen die Originaldefinition der Umfrage validiert.
    Bei Fehler â†’ Seite neu rendern mit Fehlermeldung (kein Redirect).

    ROUTE GUARDING:
    survey_max_step wird nur erhöht, wenn die Validierung erfolgreich war.
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
    # Serverseitige Pflichtfeld-Prüfung (Kap. 11)
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

    # Maximalen erlaubten Schritt erhöhen (Route Guarding)
    naechster_step = step + 1
    session['survey_max_step'] = max(session.get('survey_max_step', 0), naechster_step)

    # -------------------------------------------------------
    # Letzte Frage beantwortet â†’ Payload-Integrität prüfen & Absenden
    # -------------------------------------------------------
    if naechster_step >= total:
        return redirect(url_for('survey_submit'))

    return redirect(url_for('survey', role=role, step=naechster_step))


@app.route('/survey/back', methods=['POST'])
def survey_back():
    """Geht eine Frage zurück. Speichert die aktuelle Antwort ohne Validierung
    (Pflichtfeld-Prüfung gilt nur beim Vorwärtsgehen, nie beim Zurückgehen)."""
    role        = request.form.get('role', 'student')
    step        = request.form.get('step', 0, type=int)
    question_id = request.form.get('question_id', '')
    survey_data = session.get('survey_data')
    questions   = survey_data.get('questions', []) if survey_data else []
    if 0 <= step < len(questions):
        answer = lese_antwort_aus_formular(questions[step])
    else:
        answer = request.form.get('answer', '').strip()

    # Antwort auch beim Zurückgehen speichern (falls bereits ausgefüllt)
    if not antwort_ist_leer(answer):
        answers = session.get('survey_answers', {})
        answers[question_id] = answer
        session['survey_answers'] = answers

    prev_step = max(0, step - 1)
    return redirect(url_for('survey', role=role, step=prev_step))


@app.route('/survey/submit', methods=['GET'])
def survey_submit():
    """Finaler Abschluss der Umfrage.

    PAYLOAD-INTEGRITÄT (vgl. requirements.md Kap. 11):
    Vor dem Senden an das Backend wird geprüft, ob alle Pflichtfragen
    beantwortet wurden. Fehlt eine Antwort, wird der Nutzer zur ersten
    unbeantworteten Frage zurückgeleitet.

    MISSBRAUCHSSCHUTZ (vgl. requirements.md Kap. 10):
    Nach erfolgreichem Absenden wird ein Cookie gesetzt, der eine
    erneute Teilnahme für 30 Tage blockiert (Frictionless Security).
    """
    survey_data = session.get('survey_data')
    answers     = session.get('survey_answers', {})
    role        = session.get('survey_role', 'student')

    if not survey_data:
        flash("Keine Umfragedaten gefunden. Bitte starten Sie erneut.")
        return redirect(url_for('index'))

    questions = survey_data.get('questions', [])
    letzter_step = max(len(questions) - 1, 0)

    # -------------------------------------------------------
    # Payload-Integrität prüfen: Alle Pflichtfelder beantwortet?
    # -------------------------------------------------------
    fehlende_fragen = pruefe_payload_integritaet(survey_data, answers)
    if fehlende_fragen:
        # Zur ersten unbeantworteten Pflichtfrage zurückleiten
        questions = survey_data.get('questions', [])
        fragen_ids = [f['id'] for f in questions]
        erste_fehlende_idx = 0
        for idx, fid in enumerate(fragen_ids):
            if fid in fehlende_fragen:
                erste_fehlende_idx = idx
                break

        flash(f"Bitte beantworten Sie alle Pflichtfragen. "
              f"{len(fehlende_fragen)} Pflichtfrage(n) fehlen noch.")
        # survey_max_step zurücksetzen, damit der Nutzer wieder vorankommen kann
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
        antwort = requests.post(
            f"{BACKEND_API_URL}/results",
            json=payload,
            headers=get_auth_headers(),
            timeout=5
        )
        if not antwort.ok:
            meldung = "Unbekannter Fehler"
            try:
                meldung = antwort.json().get("message", meldung)
            except ValueError:
                if antwort.text:
                    meldung = antwort.text[:200]
            flash(f"Ergebnisse konnten nicht gespeichert werden: {meldung}", "error")
            session['survey_max_step'] = letzter_step
            return redirect(url_for('survey', role=role, step=letzter_step))
    except requests.RequestException as e:
        print(f"Warnung: Fehler beim Senden der Ergebnisse ({e}).")
        flash("Ergebnisse konnten nicht gespeichert werden, weil das Backend nicht erreichbar ist.", "error")
        session['survey_max_step'] = letzter_step
        return redirect(url_for('survey', role=role, step=letzter_step))

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
    # survey_completed_<survey_id>=saved verhindert erneute Teilnahme
    # -------------------------------------------------------
    antwort = render_template('success.html')
    response = app.make_response(antwort)
    response.set_cookie(
        key=f"survey_completed_{survey_id}",
        value="saved",
        max_age=30 * 24 * 60 * 60,  # 30 Tage in Sekunden
        httponly=True,               # Nicht per JavaScript auslesbar
        samesite='Lax'
    )
    return response

# ==============================================================
# Routen: Admin Dashboard & Verwaltung
# ==============================================================

# Pfad zum Backend-Datenverzeichnis (für direkten Dateizugriff als Fallback)
import pathlib
BACKEND_DATEN_PFAD = pathlib.Path(__file__).parent.parent / "backend" / "data"

def lade_alle_umfragen():
    import requests
    try:
        res = requests.get(f"{BACKEND_API_URL}/surveys", headers=get_auth_headers(), timeout=2)
        if res.ok:
            return res.json()
    except Exception as e:
        print(f"Fehler beim Laden aller Umfragen: {e}")
    return []

def lade_ergebnisse():
    import csv, io, requests, time
    ergebnisse_dict = {}
    try:
        t = int(time.time())
        res = requests.get(f"{BACKEND_API_URL}/results?t={t}", headers=get_auth_headers(), timeout=2)
        if res.status_code == 401:
            raise PermissionError("Sitzung abgelaufen")
        if res.ok:
            csv_data = res.text
            if csv_data.startswith('﻿'):
                csv_data = csv_data[1:]

            f = io.StringIO(csv_data)
            reader = csv.reader(f, delimiter=';')
            try:
                next(reader)  # Header
            except StopIteration:
                return []

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
                ergebnisse_dict[result_id]["answers"][question_id] = parse_csv_antwort(answer)
    except PermissionError:
        raise
    except Exception as e:
        print(f"Fehler beim Laden/Parsen der API-Ergebnisse: {e}")
        if not DEV_MODE:
            raise e
    return list(ergebnisse_dict.values())

@app.route('/admin', methods=['GET'])
@login_required
def admin():
    """Admin-Dashboard: Lädt alle Umfragen, Ergebnisse und Statistiken für die 3-Tab-Ansicht.
    Statistiken werden serverseitig berechnet für die HTML/CSS-Balkengrafik (Kap. 12.1 Funktion 1.4)."""
    try:
        alle_ergebnisse = lade_ergebnisse()
    except PermissionError:
        session.clear()
        flash("Ihre Sitzung ist abgelaufen. Bitte loggen Sie sich neu ein.")
        return redirect(url_for('login_page'))

    alle_umfragen = lade_alle_umfragen()
    aktive_ids = {u.get('survey_id') for u in alle_umfragen if u.get('survey_id')}
    alle_ergebnisse = [r for r in alle_ergebnisse if r.get('survey_id') in aktive_ids]
    
    # Antwortstatistiken für Balkengrafik serverseitig berechnen (kein JS, vgl. Kap. 12.4)
    alle_statistiken = berechne_statistiken(alle_umfragen, alle_ergebnisse)
    
    # Teilnahme-Statistiken berechnen
    teilnahme_gesamt = len(alle_ergebnisse)
    teilnahme_nach_umfrage = {u.get('survey_id'): 0 for u in alle_umfragen}
    for r in alle_ergebnisse:
        sid = r.get('survey_id')
        if sid in teilnahme_nach_umfrage:
            teilnahme_nach_umfrage[sid] += 1
        else:
            teilnahme_nach_umfrage[sid] = 1

    # Fragen-Map fuer Klarnamen-Anzeige in Einzelergebnissen aufbauen
    fragen_map = {}
    for u in alle_umfragen:
        sid = u.get('survey_id')
        fragen_map[sid] = {}
        for q in u.get('questions', []):
            fragen_map[sid][q['id']] = q.get('label', q['id'])
            # Legacy-Mapping
            if q['id'].startswith('q'):
                alt_id = 'p' + q['id'][1:]
                fragen_map[sid][alt_id] = q.get('label', q['id'])
            elif q['id'].startswith('p'):
                alt_id = 'q' + q['id'][1:]
                fragen_map[sid][alt_id] = q.get('label', q['id'])

    # Links für Linkerstellung laden
    links = {}
    try:
        import requests
        res = requests.get(f"{BACKEND_API_URL}/links", headers=get_auth_headers(), timeout=2)
        if res.ok:
            links = res.json()
    except Exception as e:
        print(f"Fehler beim Laden der Links: {e}")

    resp = make_response(render_template('admin.html',
                                         umfragen=alle_umfragen,
                                         ergebnisse=alle_ergebnisse,
                                         statistiken=alle_statistiken,
                                         teilnahme_gesamt=teilnahme_gesamt,
                                         teilnahme_nach_umfrage=teilnahme_nach_umfrage,
                                         fragen_map=fragen_map,
                                         links=links))
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
    alle_umfragen = lade_alle_umfragen()
    aktive_ids = {u.get('survey_id') for u in alle_umfragen if u.get('survey_id')}
    alle_ergebnisse = [r for r in alle_ergebnisse if r.get('survey_id') in aktive_ids]

    # CSV im Arbeitsspeicher aufbauen (kein temporäres File auf der Festplatte)
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
            schreiber.writerow([eid, zeitpunkt, sid, frage_id, formatiere_export_antwort(antwort)])

    # UTF-8 mit BOM für korrekte Darstellung in Excel (ü, ä, ö)
    csv_inhalt = '\ufeff' + ausgabe.getvalue()

    dateiname = f"umfrage_ergebnisse_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_inhalt,
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{dateiname}"'}
    )

@app.route('/api/surveys', methods=['GET'])
@login_required
def api_get_survey():
    import json as json_mod
    survey_id = request.args.get('survey_id', '')
    try:
        url = f"{BACKEND_API_URL}/surveys/{survey_id}" if survey_id else f"{BACKEND_API_URL}/surveys"
        response = requests.get(
            url,
            headers=get_auth_headers(),
            timeout=2
        )
        if response.status_code == 401:
            session.clear()
            return json_mod.dumps({"status": "error", "message": "Sitzung abgelaufen."}), 401, {"Content-Type": "application/json; charset=utf-8"}
        return response.text, response.status_code, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": f"Verbindungsfehler zum Backend: {e}"}), 503, {"Content-Type": "application/json; charset=utf-8"}

@app.route('/admin/surveys/save', methods=['POST'])
@login_required
def survey_save_local():
    import json as json_mod
    nutzlast = request.get_json(silent=True)
    if not nutzlast:
        return json_mod.dumps({"status": "error", "message": "Kein gültiger JSON-Body empfangen."}), 400, {"Content-Type": "application/json; charset=utf-8"}

    survey_id = nutzlast.get("survey_id", "")
    try:
        if survey_id:
            # Update existing -> PUT
            antwort = requests.put(
                f"{BACKEND_API_URL}/surveys/{survey_id}",
                json=nutzlast,
                headers={**get_auth_headers(), "Content-Type": "application/json"},
                timeout=2
            )
        else:
            # Create new -> POST
            antwort = requests.post(
                f"{BACKEND_API_URL}/surveys",
                json=nutzlast,
                headers={**get_auth_headers(), "Content-Type": "application/json"},
                timeout=2
            )
        if antwort.status_code == 401:
            session.clear()
            return json_mod.dumps({"status": "error", "message": "Sitzung abgelaufen. Bitte neu anmelden."}), 401, {"Content-Type": "application/json; charset=utf-8"}
        return antwort.text, antwort.status_code, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": f"Verbindungsfehler zum Backend: {e}"}), 503, {"Content-Type": "application/json; charset=utf-8"}

@app.route('/admin/surveys/delete/<survey_id>', methods=['POST'])
@login_required
def survey_delete(survey_id):
    import json as json_mod
    try:
        antwort = requests.delete(
            f"{BACKEND_API_URL}/surveys/{survey_id}",
            headers=get_auth_headers(),
            timeout=2
        )
        if antwort.status_code == 401:
            session.clear()
            return json_mod.dumps({"status": "error", "message": "Sitzung abgelaufen. Bitte neu anmelden."}), 401, {"Content-Type": "application/json; charset=utf-8"}
        if antwort.status_code == 204:
            return json_mod.dumps({"status": "deleted"}), 200, {"Content-Type": "application/json; charset=utf-8"}
        return json_mod.dumps({"status": "error", "message": "Fehler beim Löschen"}), antwort.status_code, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": f"Verbindungsfehler zum Backend: {e}"}), 503, {"Content-Type": "application/json; charset=utf-8"}

@app.route('/admin/links', methods=['GET', 'POST'])
@login_required
def manage_links():
    import requests, json as json_mod
    if request.method == 'POST':
        nutzlast = request.get_json(silent=True)
        try:
            res = requests.post(
                f"{BACKEND_API_URL}/links",
                json=nutzlast,
                headers={**get_auth_headers(), "Content-Type": "application/json"},
                timeout=2
            )
            return res.text, res.status_code, {"Content-Type": "application/json; charset=utf-8"}
        except Exception as e:
            return json_mod.dumps({"status": "error", "message": str(e)}), 503, {"Content-Type": "application/json; charset=utf-8"}
    else:
        try:
            res = requests.get(f"{BACKEND_API_URL}/links", headers=get_auth_headers(), timeout=2)
            return res.text, res.status_code, {"Content-Type": "application/json; charset=utf-8"}
        except Exception as e:
            return json_mod.dumps({"status": "error", "message": str(e)}), 503, {"Content-Type": "application/json; charset=utf-8"}

@app.route('/admin/links/<link_id>', methods=['DELETE'])
@login_required
def remove_link(link_id):
    import requests, json as json_mod
    try:
        res = requests.delete(f"{BACKEND_API_URL}/links/{link_id}", headers=get_auth_headers(), timeout=2)
        if res.status_code == 204:
            return json_mod.dumps({"status": "deleted"}), 200, {"Content-Type": "application/json; charset=utf-8"}
        return res.text, res.status_code, {"Content-Type": "application/json; charset=utf-8"}
    except Exception as e:
        return json_mod.dumps({"status": "error", "message": str(e)}), 503, {"Content-Type": "application/json; charset=utf-8"}

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
