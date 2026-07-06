# Projektanforderungen und Technische Spezifikation: Umfrage-Tool (Evaluation "Ask Alma")

Diese Dokumentation dient als unumstößliche Definition of Done (DoD) und exakte technische Spezifikation für das Projekt. Sie ist in einem rein professionellen, sachlichen und akademischen Ton verfasst. Die Verwendung von Emojis oder informellen Symbolen ist in der gesamten Dokumentation untersagt.

---

## 1. Systemarchitektur und API-Vertrag
Das System basiert auf einer verteilten Client-Server-Architektur. Der Server (Backend) arbeitet absolut zustandslos (stateless). Es werden keine In-Memory-Verkettungen, Sessions oder serverseitig gespeicherten Zustände zwischen den einzelnen HTTP-Anfragen am Backend verwaltet.

### 1.1 Übersicht der API-Endpunkte

| Ressource | URL | HTTP-Methode | Beschreibung | Erwartete HTTP-Statuscodes |
|---|---|---|---|---|
| **Health** | `/api/health` | `GET` | Überprüfung der Backend-Erreichbarkeit | `200 OK`, `503 Service Unavailable` |
| **Login** | `/api/login` | `POST` | Admin-Authentifizierung via Credentials | `200 OK` (liefert JWT), `401 Unauthorized` |
| **Survey** | `/api/survey` | `GET` | Abruf der Umfragedefinition (optional mit `?role=...`) | `200 OK`, `404 Not Found` |
| **Survey** | `/api/surveys` | `POST` | Erstellen oder Ändern einer Umfragedefinition (Admin, geschützt) | `201 Created`, `400 Bad Request`, `401 Unauthorized` |
| **Results** | `/api/results` | `POST` | Einreichen von Umfrageergebnissen | `201 Created`, `400 Bad Request` |
| **Results** | `/api/results` | `GET` | Abruf aller eingegangenen Ergebnisse für den Admin (geschützt) | `200 OK`, `401 Unauthorized` |
| **Survey** | `/api/surveys/{survey_id}` | `DELETE` | Löschen einer Umfragedefinition (Admin, geschützt) | `204 No Content`, `401 Unauthorized`, `404 Not Found` |

### 1.2 Sicherheitsvorgaben (JWT-Token und Rollen)
* **Öffentliche Endpunkte (keine Authentifizierung erforderlich):** `GET /api/health`, `POST /api/login`, `GET /api/survey` (mit optionaler Rolle), `POST /api/results`.
* **Geschützte Endpunkte (JWT-Token im Header `Authorization: Bearer <token>` erforderlich):** `POST /api/surveys`, `GET /api/results`, `DELETE /api/surveys/{survey_id}`.
* Bei fehlendem oder ungültigem Token antwortet der Server mit `401 Unauthorized`. Besitzt das Token nicht die Rolle `admin`, antwortet der Server mit `403 Forbidden`.

---

## 2. Datenmodelle und Payloads

### 2.1 Umfragedefinition (GET `/api/survey`)
Die Definition einer Umfrage wird im JSON-Format übertragen und enthält Metadaten sowie ein Fragen-Array.

```json
{
  "survey_id": "ask_alma_eval_student_v1",
  "title": "Ask Alma - Evaluation für Studierende",
  "questions": [
    {
      "id": "q1",
      "type": "text",
      "label": "Welche Erfahrungen haben Sie bisher mit 'Ask Alma' gemacht?",
      "required": true
    },
    {
      "id": "q2",
      "type": "single_choice",
      "label": "Wie bewerten Sie die Nützlichkeit von 'Ask Alma'?",
      "required": true,
      "options": [
        { "value": "täglich", "text": "Täglich" },
        { "value": "nie", "text": "Nie" }
      ]
    },
    {
      "id": "q3",
      "type": "multiple_choice",
      "label": "In welchen Bereichen nutzen Sie das Tool?",
      "required": false,
      "options": [
        { "value": "prüfungsvorbereitung", "text": "Prüfungsvorbereitung" },
        { "value": "recherche", "text": "Recherche" }
      ]
    },
    {
      "id": "q4",
      "type": "rating",
      "label": "Geben Sie eine Gesamtbewertung ab (1 bis 5 Sterne):",
      "required": true
    }
  ]
}
```

### 2.2 Antwort-Payload (POST `/api/results`)
Die Antworten werden als JSON-Objekt übertragen.

```json
{
  "survey_id": "ask_alma_eval_student_v1",
  "timestamp": "2026-07-06T13:46:00Z",
  "answers": {
    "q1": "Es hilft mir sehr bei der Prüfungsvorbereitung.",
    "q2": "täglich",
    "q3": "prüfungsvorbereitung,recherche",
    "q4": "5"
  }
}
```

---

## 3. Client-Spezifikationen und State Management

### 3.1 Dynamisches UI-Rendering
Der Client generiert HTML-Formulare zur Laufzeit vollautomatisch und typgerecht auf Basis des vom Server gelieferten JSON-Objekts.
* **Typ `text`**: Generierung einer HTML-Textarea.
* **Typ `single_choice`**: Generierung von Radio-Buttons.
* **Typ `multiple_choice`**: Generierung von Checkboxen.
* **Typ `rating`**: Generierung einer 1-5 Skala.

### 3.2 Client-Zustandsmanagement (States)
Der Client durchläuft folgende Phasen:
1. **Init**: Laden und Verarbeiten der Umfragedefinition von der API.
2. **In-Progress**: Interaktive Beantwortung. Der Client erzwingt ein Route Guarding, um ein Überspringen von Fragen zu verhindern.
3. **Submitting**: Daten werden zu einem JSON-Payload aggregiert und asynchron versendet. Die UI wird während der Übertragung blockiert (Deaktivierung aller Buttons und Ladeanzeige).
4. **Completed**: Erfolgreiches Senden, Bereinigung der Session-Daten und Setzen des Cookies.

### 3.3 Speicher und Sicherheit
* **Missbrauchsschutz (Completed-Cookie):** Nach erfolgreichem Absenden wird ein Cookie namens `survey_completed_<survey_id>` gesetzt (Ablaufzeit: 30 Tage, `httponly=True`, `samesite=Lax`). Bei erneutem Aufruf blockiert der Client den API-Aufruf autonom und zeigt die Danke-Seite.
* **JWT-Verarbeitung:** Das Admin-JWT wird im Authorization-Header (`Authorization: Bearer <token>`) mitgeführt. Bei einer HTTP `401 Unauthorized` Antwort des Servers wird die Client-Session sofort verworfen und ein Redirect zur Login-Seite durchgeführt.

### 3.4 Bereinigung des Admin-Headers und automatisches Session-Handling
* Oben rechts im Admin-Header befindet sich ausschließlich ein einziger "Logout"-Button.
* Alle redundanten Navigationselemente wie "Abmelden", "Zurück zur Startseite" oder "Lockout" sind vollständig entfernt.
* Beim Klick auf "Logout" wird das JWT-Token deterministisch gelöscht und der Benutzer direkt auf die öffentliche Login- und Startseite geleitet.
* **Automatischer Logout bei URL-Wechsel:** Navigiert ein angemeldeter Administrator manuell aus dem Admin-Bereich heraus (z. B. durch Eingabe einer anderen URL wie der Startseite oder der Umfrage-Teilnahmeseite), wird die Session serverseitig beim Abfangen der Anfrage sofort und automatisch gelöscht. Das JWT-Token wird ohne manuelle Interaktion verworfen, um den Administrator-Zustand vollständig zu bereinigen.

---

## 4. Server-Spezifikationen und Datenhaltung

### 4.1 Persistenz
* **Umfragen:** Persistierung als JSON-Dateien im Backend-Verzeichnis.
* **Ergebnisse:** Persistierung relational in CSV-Dateien (`results_<survey_id>.csv`). Der Speicherprozess arbeitet strikt append-only (Immutability by Design). Ein Ändern oder Löschen von Datensätzen via API ist nicht zulässig.
* Das Spaltenformat der CSV lautet: `result_id;timestamp;survey_id;question_id;answer`.

### 4.2 Serverseitige Strikt-Validierung (Single Source of Truth)
Bei einem `POST /api/results` validiert der Server zwingend:
1. **Payload-Format:** Request-Body ist strukturell valides JSON.
2. **Referenzielle Integrität:** Die übergebene `survey_id` existiert im Dateisystem.
3. **Vollständigkeit:** Alle Pflichtfelder (`required: true`) enthalten eine nicht-leere Antwort.
4. **Wertebereich:** Die eingereichten Werte entsprechen exakt den in der Definition spezifizierten `value`-Optionen.

Schlägt eine Validierung fehl, wird die Speicherung verweigert (kein Schreibzugriff) und ein HTTP `400 Bad Request` mit Fehlerbeschreibung im JSON-Body zurückgegeben.

---

## 5. Spezifikation der Admin-Oberfläche

### 5.1 Bereich Ergebnisse anzeigen
Die Darstellung im Tab "Ergebnisse anzeigen" erfolgt in folgender hierarchischer Reihenfolge:
* **Sektion 1 (Oben - Priorität 1):** Aggregierte Auswertung (Durchschnittswerte, Häufigkeiten der Antworten) als visuelle Balkendiagramme. Ein Button "CSV exportieren" ist direkt in dieser Sektion platziert, um den sofortigen Export der Daten zu ermöglichen.
* **Sektion 2 (Unten - Priorität 2):** Darunter folgt die Sektion für die einzelnen, eingegangenen Rohdaten aus der CSV-Datei.
* **Button-Platzierung in Sektion 2:** Der zweite "CSV exportieren"-Button für den Rohdaten-Export befindet sich auf Höhe der Überschrift dieser zweiten Sektion ("Eingegangene Ergebnisse"), rechts neben der Überschrift angeordnet. Darunter folgt die chronologische Tabelle der Einzeldaten.

### 5.2 Bereich Umfragen bearbeiten
Das Bearbeiten und Aktualisieren bestehender Umfragen wird wie folgt geregelt:
1. Der Client lädt die bestehende Struktur via `GET /api/survey?role=admin` (oder mit entsprechender Rolle).
2. Nach Modifikation im Formular-Editor sendet der Client die aktualisierte Struktur via `POST /api/surveys` an das Backend.
3. Das Backend nimmt den Request unter JWT-Absicherung entgegen, validiert die Definition und überschreibt die bestehende JSON-Datei im Dateisystem.

---

## 6. Strikte Format- und UI-Vorgaben: Verbot von Emojis und grafischen Symbolen
* Im gesamten Projekt – sowohl in allen Dokumentationsdateien als auch im Quellcode und der gesamten grafischen Benutzeroberfläche (UI) – ist die Verwendung von Emojis, Piktogrammen, grafischen Symbolen (z. B. SVG-Icons) oder Sonderzeichen (wie Pfeilen, Häkchen oder Warndreiecken) strengstens untersagt.
* Jegliche visuelle Kennzeichnung oder Navigation hat ausschließlich über rein sachlichen, professionellen Text zu erfolgen.

---

## 7. Systemweites einheitliches Benachrichtigungssystem
Für alle Systemmeldungen der Anwendung (wie Download-Bestätigungen, Pflichtfeldwarnungen, Erfolgsmeldungen und Fehlermeldungen) gilt ein einheitliches Benachrichtigungssystem:

### 7.1 Einmaligkeits-Prinzip
* Vor dem Rendern einer Meldung muss das Frontend prüfen, ob dieselbe Meldung aktuell bereits angezeigt wird.
* Jede spezifische Benachrichtigung darf zu jedem Zeitpunkt maximal einmal im Sichtfeld des Nutzers existieren. Redundante Doppelmeldungen sind technisch zu blockieren.

### 7.2 Farbcodierung nach Dringlichkeit
* **Rot (Handlungsaufforderung und Fehler):** Meldungen, bei denen der Benutzer aktiv handeln muss oder ein Fehler vorliegt (nicht ausgefüllte Pflichtfragen, ungültige Wertebereiche, Serververbindungsfehler, fehlgeschlagener Login), müssen in Rot gerendert werden.
* **Blau (Rein informativ und Erfolg):** Meldungen informativen Charakters oder Erfolgsbestätigungen (erfolgreicher Datei-Export, erfolgreiches Absenden der Antworten, erfolgreicher Login) müssen in Blau gerendert werden.

### 7.3 Automatisches Ausblenden (Timeout)
* Blaue Meldungen (Informationen und Erfolge) müssen nach 5 bis 10 Sekunden automatisch und ohne Benutzerinteraktion aus der UI ausgeblendet werden.
* Rote Meldungen (Fehler) bleiben dauerhaft sichtbar, bis der Fehler behoben wurde oder die Meldung vom Benutzer manuell geschlossen wird.

### 7.4 Positionierung
* Alle globalen Statusmeldungen werden einheitlich ganz oben im sichtbaren Bereich der Benutzeroberfläche platziert.
