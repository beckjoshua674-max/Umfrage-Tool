# Projektanforderungen: Umfrage-Tool (Evaluation „Ask Alma“)

## 1. Projektübersicht (Modul: Verteilte Systeme)
Entwicklung einer Web-Anwendung zur Durchführung von Umfragen im Rahmen des Moduls **„Verteilte Systeme“**. Der initiale Fokus liegt auf der Evaluation des Nutzens des KI-Tools „Ask Alma“. 
Aufgrund des Modulkontexts muss das System zwingend verteilte Architekturprinzipien (z. B. saubere Client-Server-Trennung, lose Kopplung über Schnittstellen) aufweisen. Das System muss generisch aufgebaut sein, um perspektivisch für beliebige weitere Umfragen nutzbar zu sein.

## 2. Projektmanagement & Multi-Agenten-Workflow
* **KI-Tool-Stack:** Die Entwicklung und Planung erfolgt im Zusammenspiel der KI-Systeme **Codex** und **Antigravity**. 
* **Single Source of Truth:** Diese `requirements.md` ist das zentrale Synchronisationsdokument für beide Tools. Vor jeder neuen Implementierungsphase ist der aktuelle Stand dieses Dokuments auszulesen.
* **Update-Pflicht:** Sobald Anforderungen im Projektverlauf (egal mit welchem Tool) verfeinert oder geändert werden, ist diese Datei zwingend und umgehend zu aktualisieren.
* **Chat-Verfeinerungen:** Wenn Anforderungen im Chat mit Codex konkretisiert, geändert oder neu entschieden werden, muss Codex diese Anpassungen unmittelbar in dieser `requirements.md` nachpflegen.
* **Timebox für den ersten Prototyp (V1):** max. 1–2 Stunden.

## 3. Architektur & Prinzipien Verteilter Systeme (Fokus V1)
* **Client-Server-Architektur:** Das System muss aus einem strikt getrennten Frontend (Client) und einem Backend (Server) bestehen.
* **Schnittstellen-Kommunikation:** Der Datenaustausch zwischen Client und Server erfolgt zustandslos (stateless) über eine definierte API (RESTful oder vergleichbar) im JSON-Format.
* **Trennung von Logik und Daten:** Die Umfrage-Definitionen (Fragen, Antwortmöglichkeiten) werden als JSON-Konfiguration vom Backend verwaltet und dynamisch über die API an den Client ausgeliefert.

## 4. Funktionale Anforderungen (Prototyp V1)
* **Umfrage-Engine (Client):** Dynamischer Aufbau des Fragebogens basierend auf der API-Antwort. Unterstützung für Freitext, Multiple-Choice und Likert-Skalen. Navigation durch die Umfrage.
* **Datenspeicherung (Server):** Ein API-Endpunkt (z. B. `POST /api/results`), der die Antworten vom Client entgegennimmt und speichert (für V1 reicht eine lokale Dateiablage als JSON/CSV oder eine leichtgewichtige Datenbank wie SQLite).

## 5. UI & Design (Corporate Identity)
* Das Frontend muss sich am Corporate Design der Hochschule orientieren.
* **Referenz:** https://www.hs-kehl.de/
* Das Design (Farbschema, Typografie) der Referenzseite ist via CSS auf das Umfrage-Tool anzuwenden.

## 6. Zukünftige Ausbaustufen (Out of Scope für V1)
* **Containerisierung:** Bereitstellung von Client, Server und Datenbank als unabhängige Docker-Container.
* **Automatisierung:** Vollautomatisierte Dokumentation und Agenten-Steuerung via `Agents.md`.
* **Microservices:** Auslagerung von Diensten (z. B. Authentifizierung, Daten-Auswertung).

## 7. API-Schnittstellen (Frontend <-> Backend)
Diese Schnittstellen müssen vom Backend (Codex) bereitgestellt und vom Frontend (Antigravity) konsumiert werden. Die Kommunikation erfolgt zustandslos über HTTP-REST.

**Sicherheitsvorgabe (JWT-Token & Rollen):**
- **Öffentliche Endpunkte (kein Token nötig):** `GET /api/health`, `POST /api/login`, `GET /api/survey`, `POST /api/results`.
- **Geschützte Endpunkte (JWT-Token im Header `Authorization: Bearer <token>` erforderlich, nur Admin):** `POST /api/surveys`, `GET /api/results`, `DELETE /api/surveys/{survey_id}`.
- Wird ein geschützter Endpunkt ohne oder mit ungültigem Token aufgerufen, muss das Backend mit `401 Unauthorized` antworten. Besitzt der Token nicht die Rolle `admin`, wird `403 Forbidden` zurückgegeben.

---

### 7.1 GET `/api/health`
- **Beschreibung:** Überprüft die Erreichbarkeit und Betriebsbereitschaft des Backends.
- **Anfrage:** Keine Parameter, kein Body.
- **Antworten:**
  - **`200 OK`**: Backend ist voll funktionsfähig.
    ```json
    { "status": "ok", "service": "ask-alma-backend" }
    ```
  - **`503 Service Unavailable`**: Backend oder kritische Subsysteme sind nicht erreichbar.

### 7.2 POST `/api/login`
- **Beschreibung:** Authentifizierung für den administrativen Zugang.
- **Anfrage-Payload (JSON):**
  ```json
  {
    "username": "admin",
    "password": "..."
  }
  ```
- **Antworten:**
  - **`200 OK`**: Erfolgreich authentifiziert. Liefert JWT-Token und Rolle.
    ```json
    {
      "token": "jwt_token_xyz",
      "role": "admin"
    }
    ```
  - **`401 Unauthorized`**: Ungültige Anmeldedaten.
    ```json
    { "status": "error", "message": "Ungültiger Benutzername oder Passwort" }
    ```

### 7.3 GET `/api/survey`
- **Beschreibung:** Liefert die Struktur und Fragen einer Umfrage. **Kein Token erforderlich.**
- **Query-Parameter:** `role` (optional, Werte: `student` oder `professor`). Bestimmt, welche Umfragedefinition geladen wird. Standardwert ist `student`.
- **Antworten:**
  - **`200 OK`**: Liefert die Umfragedefinition im JSON-Format.
    ```json
    {
      "survey_id": "ask_alma_eval_student",
      "title": "Evaluation Ask Alma",
      "questions": [
        {
          "id": "q1",
          "type": "single_choice",
          "label": "Wie oft nutzen Sie Ask Alma?",
          "required": true,
          "options": [
            { "value": "taeglich", "text": "Täglich" },
            { "value": "nie", "text": "Nie" }
          ]
        }
      ]
    }
    ```
  - **`404 Not Found`**: Die angeforderte Umfrage für die Rolle existiert nicht.

### 7.4 POST `/api/surveys`
- **Beschreibung:** Erstellt eine neue Umfragedefinition oder überschreibt eine bestehende. **Nur für Admin.**
- **Header:** `Authorization: Bearer <token>`
- **Anfrage-Payload (JSON):** Das vollständige JSON-Objekt der Umfragedefinition (analog zu GET `/api/survey`).
- **Antworten:**
  - **`201 Created`**: Erfolgreich gespeichert.
    ```json
    { "status": "created", "survey_id": "ask_alma_eval_student" }
    ```
  - **`400 Bad Request`**: Fehlerhafte Definition (z.B. fehlende Pflichtfelder im JSON-Modell).
  - **`401 Unauthorized`**: Token fehlt oder ist ungültig.
  - **`403 Forbidden`**: Token gültig, aber unzureichende Berechtigungen (kein Admin).

### 7.5 POST `/api/results`
- **Beschreibung:** Übermittelt die ausgefüllten Antworten einer Umfrage zur persistenten Speicherung. **Kein Token erforderlich.**
- **Anfrage-Payload (JSON):**
  ```json
  {
    "survey_id": "ask_alma_eval_student",
    "timestamp": "2026-07-06T10:00:00Z",
    "answers": {
      "q1": "taeglich"
    }
  }
  ```
- **Antworten:**
  - **`201 Created`**: Antworten wurden erfolgreich entgegengenommen und persistent in die CSV-Datei geschrieben.
    ```json
    { "status": "created", "result_id": "uuid-des-ergebnisses" }
    ```
  - **`400 Bad Request`**: Validierung fehlgeschlagen (Details im Fehlerbody).
    ```json
    { "status": "error", "message": "Pflichtfeld q1 wurde nicht ausgefüllt." }
    ```

### 7.6 GET `/api/results`
- **Beschreibung:** Ruft alle bisher eingegangenen Ergebnisse ab. **Nur für Admin.**
- **Header:** `Authorization: Bearer <token>`
- **Antworten:**
  - **`200 OK`**: Gibt die Ergebnisse als relationale CSV-Daten zurück.
    - **Content-Type:** `text/csv; charset=utf-8`
    - **Inhalt:** CSV-Format mit Spalten wie `result_id;timestamp;survey_id;question_id;answer`.
  - **`401 Unauthorized`**: Token fehlt oder ist ungültig.
  - **`403 Forbidden`**: Fehlende Admin-Rolle.

### 7.7 DELETE `/api/surveys/{survey_id}`
- **Beschreibung:** Löscht eine bestehende Umfragedefinition. **Nur für Admin.**
- **Header:** `Authorization: Bearer <token>`
- **Antworten:**
  - **`204 No Content`**: Erfolgreich gelöscht, kein Content im Body.
  - **`401 Unauthorized`**: Token fehlt oder ist ungültig.
  - **`403 Forbidden`**: Fehlende Admin-Rolle.
  - **`404 Not Found`**: Die angegebene `survey_id` existiert nicht.

## 8. Abhängigkeiten (Backend)
Für den Betrieb des Backends werden keine externen Python-Pakete benötigt. Der Server nutzt ausschließlich die Python-Standardbibliothek:
```text
Python >= 3.10
```

## 9. Abhängigkeiten (Frontend)
Die folgenden Python-Pakete werden für den Betrieb des Frontends benötigt:
```text
Flask==3.0.3
requests==2.31.0
```

## 10. Zustandsverwaltung (State Management)
Das System erzwingt eine strikte Trennung der Zustände (State), um die Architekturprinzipien verteilter Systeme einzuhalten:

**Server (Backend / Single Source of Truth):**
- **Umfragen:** Definition und Struktur der fertigen Umfragen (gespeichert als JSON, z. B. `survey_student.json`).
- **Ergebnisse:** Die finalen Daten der vollständig abgeschlossenen Umfragen werden relational in CSV-Dateien (z. B. `results_<survey_id>.csv`) gespeichert. Dies geschieht strikt **append-only** (Anhängen am Dateiende - Immutability by Design), um einen transaktionssicheren Durchsatz zu gewährleisten.
- **Hinweis:** Das Backend agiert für die eigentliche Durchführung komplett zustandslos (stateless) und verwaltet keine Nutzersessions.

**Server (Frontend / Flask):**
- **Sitzungszustand:** Verwaltung der laufenden Nutzersitzungen (via Session-Cookie).
- **In Bearbeitung:** Temporäre Speicherung der Antworten von noch nicht abgeschlossenen Umfragen (Drafts) in der Session.
- **Fortschritt:** Tracking, welche Frage aktuell bearbeitet wird und ob alle Bedingungen erfüllt wurden (`survey_max_step`).
- **Autorisierung:** Speichern des JWT-Tokens und des Admin-Status nach erfolgreichem Login.
- **Versionskontrolle:** Abgleich der Umfrageversion während der Bearbeitung (`survey_id`), um Konflikte bei zeitgleichen Änderungen zu vermeiden.

**Client (Normaler Nutzer / Browser):**
- **Flüchtiger UI-Zustand:** Die aktuellen Eingaben liegen nur im Arbeitsspeicher des Browsers (DOM), bis auf „Weiter" oder „Absenden" geklickt wird.
- **Missbrauchsschutz (Cookies - Frictionless Security):** Nach erfolgreicher Teilnahme setzt das Frontend ein langlebiges Cookie (z. B. `survey_completed_<survey_id>=true` für 30 Tage). Bei erneutem Aufruf blockiert der Client den API-Aufruf autonom und zeigt direkt die Danke-Seite.

**Client (Admin / Browser):**
- **Token-Verwaltung:** Speichert das JWT lokal (z. B. in der Session oder im localStorage) und hängt es bei jedem API-Aufruf als `Authorization: Bearer <token>` an.
- **Sicherheit bei Token-Ablauf:** Empfängt der Client bei einem API-Call einen `401 Unauthorized` Fehler, verwirft er das gespeicherte Token sofort deterministisch und erzwingt einen Redirect auf die Login-Seite.
- **Editor-Zustand:** Hält die Struktur von im Aufbau befindlichen Umfragen im Arbeitsspeicher des Browsers (via SurveyJS), bis diese gespeichert und an die API gesendet werden.

### 10.1 Client-Zustände (States)
Der Client durchläuft beim Ausfüllen einer Umfrage deterministisch folgende Phasen:
1. **Init**: Laden und Verarbeiten der Umfragedefinition von der API.
2. **In-Progress**: Interaktive Beantwortungsphase. Der Client trackt und speichert den Fortschritt und verhindert durch Route Guarding ein Überspringen von Seiten.
3. **Submitting**: Die gesammelten Antworten werden zu einem JSON-Payload aggregiert und asynchron versendet. Die UI wird für weitere Eingaben blockiert.
4. **Completed**: Die Daten wurden erfolgreich auf dem Server gesichert; das Session-State wird bereinigt und das Abschluss-Cookie im Browser verankert.

---

## 11. Ablaufsteuerung & Datenvalidierung (Server-Side Enforcement)
Um die Datenintegrität sicherzustellen und Manipulationen durch den Endnutzer zu verhindern, gelten folgende Regeln:

**Schutz vor URL-Manipulation (Route Guarding):**
Flask speichert den Fortschritt des Nutzers strikt in der serverseitigen Nutzersession (z. B. `survey_max_step`). Versucht ein Nutzer, über die URL eine Frage aufzurufen, die er noch nicht freigeschaltet hat, leitet Flask ihn automatisch via HTTP 302 Redirect auf seinen korrekten Schritt zurück.

**Serverseitige Pflichtfeld-Prüfung:**
HTML5-Validierungen (`<input required>`) dienen nur der visuellen Nutzerführung und gelten als unsicher. Bei jedem Formular-Submit prüft die Flask-Route die empfangenen Daten zwingend gegen die Original-JSON-Definition der Umfrage.

**Serverseitige Strikt-Validierung (Single Source of Truth im Backend):**
Das Backend vertraut dem Client nicht. Bei einem `POST /api/results` validiert der Server den Payload zwingend anhand folgender Kriterien:
1. **Payload-Format:** Ist der übermittelte Request-Body strukturell valides JSON?
2. **Referenzielle Integrität:** Existiert die im Payload übergebene `survey_id` als aktive Umfragedefinition im Dateisystem des Backends?
3. **Vollständigkeit:** Sind alle in der Umfragedefinition als `required` markierten Fragen im Antwort-Payload enthalten und nicht leer?
4. **Wertebereichs-Prüfung:** Entsprechen die eingereichten Werte bei Auswahlfragen (z.B. `single_choice`, `multiple_choice`, `rating`) exakt den in der Umfragedefinition zugelassenen Schlüsseln (z.B. den Werten im `options`-Array oder dem Bereich 1-5)?

Schlägt eine dieser Validierungen fehl, lehnt das Backend die Speicherung ab, führt keinen Datei-Write aus und liefert zwingend ein **`400 Bad Request`** mit einer präzisen Fehlermeldung im JSON-Response-Body zurück.

## 12. Admin-Oberfläche: Funktionsanforderungen

Der Admin-Bereich ist in drei Tabs unterteilt. Zugang nur nach Login mit Admin-Rolle (`@login_required`).

### 12.1 Bereich „Ergebnisse anzeigen"

**Ziel:** Strukturierter Überblick über alle eingegangenen Umfrage-Antworten.

| Nr. | Funktion | Beschreibung |
|-----|----------|-------------|
| 1.1 | Umfragen-Filter | Liste aller vorhandenen Umfragen (Student / Professor). Klick filtert die Ergebnistabelle. |
| 1.2 | Ergebnistabelle | Alle Einreichungen: Zeitstempel, Umfrage-ID, kompakte Antwortvorschau (aufklappbar). |
| 1.3 | Antwortdetails | Pro Einreichung: Alle Fragen + zugehörige Antworten in lesbarer Form. |
| 1.4 | Auswertungsstatistik | Pro Umfrage: Antworthäufigkeit bei Multiple-Choice-Fragen als Balkengrafik (reines HTML/CSS, kein JS). |
| 1.5 | Ergebnis-Export | Download der Ergebnisse als CSV-Datei (Flask-Route generiert serverseitig). |

**Sicherheit:** Nur für eingeloggte Admins. Keine Ergebnisse werden gesendet, bevor der Session-Token validiert wurde.

### 12.2 Bereich „Umfragen bearbeiten"

**Ziel:** Bestehende Umfragen nachträglich anpassen ohne Neuerstellung.

| Nr. | Funktion | Beschreibung |
|-----|----------|-------------|
| 2.1 | Umfragen-Liste | Linke Seitenleiste mit allen Umfragen (Titel, Zielgruppe, Fragenanzahl). |
| 2.2 | Fragen-Editor | Klick öffnet Umfrage im Editor: Fragetext, Typ, Optionen und Pflichtfeld-Status editierbar. |
| 2.3 | Reihenfolge | Fragen per Auf/Ab-Pfeil verschieben. |
| 2.4 | Frage löschen | Einzelne Fragen entfernen (mit Bestätigungshinweis). |
| 2.5 | Frage hinzufügen | Neue Frage an beliebiger Position einfügen (Typ wählbar). |
| 2.6 | Speichern | Überschreibt `survey_student.json` bzw. `survey_professor.json` via `POST /admin/surveys/save`. |
| 2.7 | Versionswarnung | Wenn eine Umfrage bearbeitet wird, die gerade von Teilnehmern ausgefüllt wird, zeigt Flask eine Warnung (Versionskontrolle via `survey_id`, vgl. Kap. 10). |

**Sicherheit:** Speichern erfordert serverseitige Validierung: mind. 1 Frage, Titel vorhanden, Rolle gültig.

### 12.3 Bereich „Umfrage erstellen"

**Ziel:** Neue Umfragen ohne Programmierkenntnisse erstellen.

| Nr. | Funktion | Beschreibung |
|-----|----------|-------------|
| 3.1 | Metadaten | Titel (Pflicht), Beschreibung (optional), Zielgruppe: Student oder Professor. |
| 3.2 | Fragen-Builder | Dynamisches Hinzufügen von Fragen. Jede Frage: Fragetext, Typ-Auswahl, Pflichtfeld-Toggle. |
| 3.3 | Fragetypen | Freitext (Textarea), Einzelauswahl (Radio), Mehrfachauswahl (Checkbox), Bewertung 1–5. |
| 3.4 | Optionen verwalten | Bei Auswahl-Fragen: Optionen hinzufügen/entfernen. Mind. 2 Optionen (serverseitig validiert). |
| 3.5 | Reihenfolge | Fragen per Auf/Ab-Pfeil verschieben. |
| 3.6 | Speichern | Sendet JSON an `POST /admin/surveys/save`, das die Datei serverseitig schreibt. |
| 3.7 | Zurücksetzen | Formular leeren und neu beginnen. |
| 3.8 | Feedback | Klare Erfolgs-/Fehlermeldung nach dem Speichern (serverseitig, kein JS). |

**Sicherheit:** Serverseitige Validierung aller Pflichtfelder. Keine direkte Dateimanipulation vom Browser – ausschließlich über definierte Flask-Routen.

### 12.4 Gemeinsame technische Grundsatzregeln (alle 3 Bereiche)

| Regel | Umsetzung |
|-------|-----------|
| Kein JavaScript für Logik | JS nur für den Admin-Builder (erlaubte Ausnahme laut agents.md). Validierung und Navigation via Python/Flask. |
| Alle Kommentare auf Deutsch | Gilt für Python, HTML und CSS-Kommentare. |
| Login-Pflicht | Jede Admin-Route ist mit `@login_required` geschützt. |
| Serverseitige Validierung | Alle Eingaben werden in Flask gegen die Umfrage-JSON-Definition geprüft, bevor sie gespeichert werden. |

---

## 13. Regel: Zustandsdokumentation vor jeder Implementierung

**Grundsatz:** Bevor eine neue Funktion oder eine Änderung an einer bestehenden Funktion implementiert wird, müssen die betroffenen Zustände (States) vollständig definiert und in der `requirements.md` dokumentiert sein.

Diese Regel gilt für **beide Agenten (Antigravity und Codex)** und für **jeden Änderungstyp** (neue Feature, Bugfix, Refactoring).

### Was muss dokumentiert werden?

Für jede Änderung sind folgende Zustandsinformationen zu definieren und festzuhalten:

| Zustandsebene | Zu dokumentierende Informationen |
|---------------|----------------------------------|
| **Backend-Zustand** | Welche Daten werden dauerhaft gespeichert? In welcher Datei/Datenstruktur? Welches Format? |
| **Session-Zustand (Flask)** | Welche Session-Variablen werden angelegt, verändert oder gelöscht? Wann und durch welche Route? |
| **Cookie-Zustand (Client)** | Welche Cookies werden gesetzt? Name, Wert, Lebensdauer, `httponly`-Flag? |
| **UI-Zustand (Browser)** | Welche temporären Eingaben hält der Browser? Wann werden sie verworfen? |
| **Fehlerzustand** | Welche Fehler können auftreten? Wie reagiert das System (Redirect, Fehlermeldung, HTTP-Statuscode)? |

### Dokumentationspflicht vor dem Coden

Die Zustandsdefinition muss **vor oder zeitgleich** mit der Implementierung in die `requirements.md` eingetragen werden – niemals nachträglich. Ziel ist, dass der jeweils andere Agent (und der menschliche Entwickler) zu jedem Zeitpunkt den vollständigen Systemzustand aus der Dokumentation ablesen kann, ohne den Code lesen zu müssen.

### Beispiel-Struktur für eine Zustandsdefinition

```
### Zustand: Umfrage-Fortschritt (Normalnutzer)
- **Session-Variable:** `survey_max_step` (int) – höchster bisher freigeschalteter Schritt
- **Angelegt:** GET /survey?step=0 (Umfrage-Start)
- **Erhöht:** POST /survey/next (nur bei erfolgreicher Validierung)
- **Gelöscht:** GET /survey/submit (nach erfolgreichem Absenden)
- **Fehlerzustand:** Wert > aktueller step → HTTP 302 Redirect auf survey_max_step

### Zustand: Participation-Cookie (Missbrauchsschutz)
- **Cookie-Name:** `survey_completed_<survey_id>` (z. B. `survey_completed_ask_alma_student_v1`)
- **Wert:** `"true"`
- **Lebensdauer:** 30 Tage (`max_age = 2592000`)
- **Flags:** `httponly=True`, `samesite='Lax'`
- **Gesetzt durch:** GET /survey/submit (nach erfolgreichem Absenden)
- **Geprüft durch:** GET /survey?step=0 (Umfrage-Start)
- **Fehlerzustand:** Cookie vorhanden → Weiterleitung zur bereits-teilgenommen Seite

### Zustand: Admin-Session
- **Session-Variable:** `token` (str) – JWT-Token des eingeloggten Admins
- **Session-Variable:** `username` (str) – Anzeigename des Admins
- **Angelegt:** POST /login (bei erfolgreichem Login)
- **Gelöscht:** GET /logout
- **Fehlerzustand:** Kein Token → @login_required leitet auf /login um

### Zustand: CSV-Export (serverseitig, zustandslos)
- **Kein Session-Zustand** – Export wird bei jedem Aufruf frisch generiert
- **Route:** GET /admin/results/export
- **Backend-Zustand:** Liest die relationalen Ergebnisse direkt aus den append-only CSV-Dateien des Backends (`backend/data/results_<survey_id>.csv`).
- **UI-Zustand:** Browser-Download-Dialog (via Content-Disposition Header)
- **Fehlerzustand:** Keine Ergebnisse → leere CSV mit Header-Zeile (Result-ID;Timestamp;Survey-ID;Question-ID;Answer)

### Zustand: Statistik-Anzeige (Admin Tab 1)
- **Kein eigener State** – wird serverseits beim Laden von /admin berechnet
- **Flask berechnet:** Häufigkeit jeder Option pro Multiple-Choice-Frage
- **Template-Variable:** `statistiken` (dict: survey_id → frage_id → option_value → anzahl)
- **UI-Zustand:** Statische HTML/CSS-Balkengrafik, keine Interaktion

### Zustand: Umfrage-Fragetypen (Normalnutzer)
- **Fragetyp `single_choice`** (Einzelauswahl, Radio): Genau 1 Antwort erlaubt
  - **Validierung:** Serverseitig wie `multiple_choice` – Wert muss in `options.value` enthalten sein
  - **Fehlerzustand:** Kein Wert bei Pflichtfrage → Fehlermeldung, kein Vorwärts-Redirect
- **Fragetyp `rating`** (Bewertung 1–5): Ganzzahl 1–5
  - **Validierung:** Wert muss "1"–"5" sein
  - **Fehlerzustand:** Kein Wert bei Pflichtfrage → Fehlermeldung
- **Fragetyp `multiple_choice`** (Mehrfachauswahl, Checkbox): Mehrere Antworten möglich
  - **Speicherformat:** Kommaseparierter String in Session (z. B. `"opt1,opt2"`)
  - **Fehlerzustand:** Kein Wert bei Pflichtfrage → Fehlermeldung

```

