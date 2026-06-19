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
