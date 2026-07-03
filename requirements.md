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
Diese Schnittstellen müssen vom Backend (Codex) bereitgestellt und vom Frontend (Antigravity) konsumiert werden.

**Sicherheitsvorgabe (JWT-Token):**
- **Öffentliche Endpunkte (kein Token nötig):** `GET /api/health`, `POST /api/login`, `GET /api/survey`, `POST /api/results`.
- **Geschützte Endpunkte (JWT-Token im Header `Authorization: Bearer <token>` erforderlich, nur Rolle `admin`):** `POST /api/survey/questions`, `DELETE /api/survey/questions/<id>`, `GET /api/results`.
- Wird ein geschützter Endpunkt ohne oder mit ungültigem Token aufgerufen, muss das Backend mit `401 Unauthorized` antworten.

### 7.0 GET `/api/health`
- **Beschreibung:** Liefert einen einfachen Betriebsstatus des Backends, damit Frontend und Entwicklung prüfen können, ob der Server erreichbar ist.
- **Erwartete Anfrage:** Keine Query-Parameter, kein Request-Body.
- **Erwartete Antwort (JSON):**
  ```json
  {
    "status": "ok",
    "service": "ask-alma-backend"
  }
  ```
- **Statuscode:** `200 OK` bei erreichbarem Backend.

### 7.0.1 POST `/api/login`
- **Beschreibung:** Authentifiziert einen Benutzer. Aktuell ist nur die Admin-Rolle loginpflichtig.
- **Erwarteter Payload (JSON):**
  ```json
  {
    "username": "...",
    "password": "..."
  }
  ```
- **Test-Credentials (für Entwicklung):** Das Backend muss mindestens folgende Testbenutzer akzeptieren:
  - `admin` / `admin123` (Rolle: `admin`)
- **Erwartete Antwort:** Status `200 OK` mit JWT Token und der zugewiesenen Rolle.
  ```json
  {
    "token": "jwt_token_xyz",
    "role": "admin"
  }
  ```
- **Fehlerantwort:** Status `401 Unauthorized`, wenn Login fehlschlägt.

### 7.1 GET `/api/survey`
- **Beschreibung:** Liefert die Struktur und Fragen der Umfrage an das Frontend. **Kein Token erforderlich.**
- **Erwartete Anfrage:** Query-Parameter `?role=student|professor`. Das Backend **muss** je nach Rolle einen **unterschiedlichen Fragenkatalog** ausliefern. Kein Request-Body.
- **Rollenbasierte Datendateien:** Das Backend lädt die Fragen aus getrennten JSON-Dateien:
  - `backend/data/survey_student.json` → wird bei `?role=student` ausgeliefert.
  - `backend/data/survey_professor.json` → wird bei `?role=professor` ausgeliefert.
  - Fehlt der Parameter `role`, wird standardmäßig `survey_student.json` geladen.
- **Erwartete Antwort (JSON):**
  ```json
  {
    "survey_id": "ask_alma_eval_v1",
    "title": "Ask Alma - Evaluation",
    "description": "Umfrage-Tool der Hochschule Kehl zur Evaluation des Nutzens von Ask Alma.",
    "questions": [
      {
        "id": "q1",
        "type": "text",
        "label": "1. Welche Erfahrungen haben Sie bisher mit dem Tool \"Ask Alma\" gemacht?",
        "required": true
      },
      {
        "id": "q2",
        "type": "multiple_choice",
        "label": "2. Wie bewerten Sie die generelle Nützlichkeit von \"Ask Alma\" für Ihr Studium?",
        "options": [
          { "value": "sehr_nuetzlich", "text": "Sehr nützlich" },
          { "value": "wenig_nuetzlich", "text": "Wenig nützlich" }
        ],
        "required": true
      }
    ]
  }
  ```

### 7.2 POST `/api/results`
- **Beschreibung:** Sendet die ausgefüllten Umfrageantworten vom Frontend an das Backend.
- **Content-Type:** `application/json`
- **Erwarteter Payload (JSON):**
  ```json
  {
    "survey_id": "ask_alma_eval_v1",
    "timestamp": "2026-06-12T10:45:00Z",
    "answers": {
      "q1": "Antworttext...",
      "q2": "sehr_nuetzlich"
    }
  }
  ```
- **Validierungsregeln:**
  - `survey_id` muss ein nicht-leerer String sein und zur vom Backend ausgelieferten Umfrage passen.
  - `timestamp` ist optional, muss bei Übergabe aber ein ISO-8601-String sein.
  - `answers` muss ein JSON-Objekt sein, dessen Keys den Frage-IDs aus `GET /api/survey` entsprechen.
  - Pflichtfragen (`required: true`) müssen eine nicht-leere Antwort enthalten.
  - Antworten auf `multiple_choice`-Fragen müssen exakt einem `value` der jeweiligen `options` entsprechen.
- **Erwartete Antwort:** Status `201 Created` bei erfolgreicher Speicherung.
  ```json
  {
    "status": "created",
    "result_id": "uuid-der-gespeicherten-antwort"
  }
  ```
- **Erwartete Fehlerantwort:** Status `400 Bad Request`, wenn der Payload nicht valide ist.
  ```json
  {
    "status": "error",
    "message": "Beschreibung des Validierungsfehlers"
  }
  ```

### 7.3 POST `/api/survey/questions`
- **Beschreibung:** Fügt der Umfrage eine neue Frage hinzu.
- **Zugriffsbeschränkung:** Nur für Rolle `admin`. Erfordert gültiges JWT-Token im Header. Bei fehlendem oder ungültigem Token → `401 Unauthorized`. Bei gültigem Token, aber falscher Rolle → `403 Forbidden`.
- **Erwarteter Payload (JSON):** Ein einzelnes Frage-Objekt (ähnlich der Objekte in `GET /api/survey`).
- **Erwartete Antwort:** Status `201 Created`.

### 7.4 DELETE `/api/survey/questions/<id>`
- **Beschreibung:** Löscht eine bestehende Frage anhand ihrer ID.
- **Zugriffsbeschränkung:** Nur für Rolle `admin`. Erfordert gültiges JWT-Token im Header. Bei fehlendem oder ungültigem Token → `401 Unauthorized`. Bei gültigem Token, aber falscher Rolle → `403 Forbidden`.
- **Erwartete Antwort:** Status `200 OK` (oder `204 No Content`).

### 7.5 GET `/api/results`
- **Beschreibung:** Liefert alle bisher gespeicherten Umfrage-Antworten. (Wird im Admin-Dashboard genutzt)
- **Zugriffsbeschränkung:** Nur für Rolle `admin`. JWT-Token im Header erforderlich.
- **Erwartete Antwort (JSON):** Array von Ergebnis-Objekten.
  ```json
  [
    {
      "result_id": "uuid",
      "received_at": "2026-06-12T10:45:00Z",
      "survey_id": "ask_alma_eval_v1",
      "answers": {
        "q1": "Antworttext...",
        "q2": "sehr_nuetzlich"
      }
    }
  ]
  ```

### 7.6 POST `/api/surveys/create`
- **Beschreibung:** Speichert eine vollständige, neu erstellte Umfrage-Definition (erstellt via SurveyJS Creator im Admin-Bereich) als neue JSON-Datei im Backend. Ersetzt oder ergänzt die rollenbasierten Survey-Dateien.
- **Zugriffsbeschränkung:** Nur für Rolle `admin`. JWT-Token im Header `Authorization: Bearer <token>` erforderlich. Bei fehlendem oder ungültigem Token → `401 Unauthorized`. Bei falscher Rolle → `403 Forbidden`.
- **Content-Type:** `application/json`
- **Erwarteter Payload (JSON):** Ein vollständiges SurveyJS-kompatibles JSON-Objekt mit mind. folgenden Feldern:
  ```json
  {
    "survey_id": "eindeutige-id-als-string",
    "title": "Titel der Umfrage",
    "role": "student|professor",
    "questions": [
      {
        "id": "q1",
        "type": "text|multiple_choice",
        "label": "Fragetext",
        "required": true,
        "options": [
          { "value": "opt1", "text": "Anzeigetext" }
        ]
      }
    ]
  }
  ```
  - `survey_id`: Pflichtfeld. Nicht-leerer String. Wird als Dateiname verwendet (z.B. `survey_{role}.json`).
  - `role`: Pflichtfeld. Muss `student` oder `professor` sein. Bestimmt, welche Datei überschrieben wird (`survey_student.json` oder `survey_professor.json`).
  - `title`: Pflichtfeld. Nicht-leerer String.
  - `questions`: Pflichtfeld. Array mit mind. 1 Frage-Objekt.
- **Erwartete Antwort:** Status `201 Created` bei erfolgreicher Speicherung.
  ```json
  {
    "status": "created",
    "survey_id": "eindeutige-id",
    "saved_as": "survey_student.json"
  }
  ```
- **Fehlerantworten:**
  - `400 Bad Request`: Payload fehlt oder ist unvollständig.
  - `401 Unauthorized`: Token fehlt oder ist ungültig.
  - `403 Forbidden`: Rolle ist nicht `admin`.

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
- **Umfragen:** Definition und Struktur der fertigen Umfragen (JSON).
- **Ergebnisse:** Die finalen Daten der vollständig abgeschlossenen Umfragen.
- **Hinweis:** Das Backend agiert für die eigentliche Durchführung komplett zustandslos (stateless).

**Server (Frontend / Flask):**
- **Sitzungszustand:** Verwaltung der laufenden Nutzersitzungen (via Session-Cookie).
- **In Bearbeitung:** Temporäre Speicherung der Antworten von noch nicht abgeschlossenen Umfragen (Drafts).
- **Fortschritt:** Tracking, welche Frage aktuell bearbeitet wird und ob alle Bedingungen erfüllt wurden.
- **Autorisierung:** Rollenverwaltung (Sicherstellung der Admin-Rechte für den Editor).
- **Versionskontrolle:** Abgleich der Umfrageversion während der Bearbeitung, um Konflikte bei zeitgleichen Änderungen zu vermeiden.

**Client (Normaler Nutzer):**
- **Flüchtiger UI-Zustand:** Die aktuellen Eingaben liegen nur im Arbeitsspeicher des Browsers, bis auf „Weiter" oder „Absenden" geklickt wird.
- **Missbrauchsschutz (Cookies):** Nach erfolgreicher Teilnahme setzt Flask ein lokales Cookie (z. B. `survey_completed_<survey_id>=true` für 30 Tage), um einfache Mehrfachteilnahmen ohne Login-Zwang zu blockieren (Frictionless Security).

**Client (Admin):**
- **Editor-Zustand:** Hält die Struktur und die Fragen von im Aufbau befindlichen, nicht finalen Umfragen im Arbeitsspeicher des Browsers (via SurveyJS), bis diese gespeichert und ans Backend gesendet werden.

## 11. Ablaufsteuerung & Datenvalidierung (Server-Side Enforcement)
Um die Datenintegrität sicherzustellen und Manipulationen durch den Endnutzer (z. B. URL-Spoofing, Überspringen von Fragen) zu verhindern, gelten folgende serverseitige Regeln für den Frontend-Server (Flask):

**Schutz vor URL-Manipulation (Route Guarding):**
Flask speichert den Fortschritt des Nutzers strikt in der serverseitigen Nutzersession (z. B. `current_page = 1`).
Versucht ein Nutzer, über die URL eine Seite aufzurufen, die er noch nicht erreicht hat (z. B. manueller Aufruf von `/survey/page/3`, obwohl er auf Seite 1 ist), leitet Flask ihn automatisch via HTTP 302 Redirect auf seine korrekte `current_page` zurück. Dies geschieht reibungslos und unsichtbar.

**Serverseitige Pflichtfeld-Prüfung:**
HTML5-Validierungen (`<input required>`) dienen nur der visuellen Nutzerführung und gelten als unsicher ("Never trust the client").
Bei jedem Formular-Submit prüft die Flask-Route die empfangenen Daten zwingend gegen die Original-JSON-Definition der Umfrage. Fehlt die Antwort auf eine Pflichtfrage, wird der Fortschritt verweigert und die aktuelle Seite mit einer entsprechenden Fehlermeldung neu gerendert.

**Payload-Integrität beim Abschluss:**
Erst wenn Flask intern verifiziert hat, dass alle Seiten der Umfrage linear durchlaufen und alle Pflichtfelder beantwortet wurden, darf der gesammelte Zustand als finaler Payload an das Backend (`POST /api/results`) gesendet werden.

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
- **Backend-Zustand:** Liest alle JSON-Dateien aus `backend/data/results/`
- **UI-Zustand:** Browser-Download-Dialog (via Content-Disposition Header)
- **Fehlerzustand:** Keine Ergebnisse → leere CSV mit Header-Zeile

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

