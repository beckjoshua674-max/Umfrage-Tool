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
| **Survey** | `/api/surveys` | `GET` | Abruf der Umfragedefinition (optional mit `?role=...`) | `200 OK`, `404 Not Found` |
| **Survey** | `/api/surveys` | `POST` | Erstellen oder Ändern einer Umfragedefinition (Admin, geschützt) | `201 Created`, `400 Bad Request`, `401 Unauthorized` |
| **Results** | `/api/results` | `POST` | Einreichen von Umfrageergebnissen | `201 Created`, `400 Bad Request` |
| **Results** | `/api/results` | `GET` | Abruf aller eingegangenen Ergebnisse für den Admin (geschützt) | `200 OK`, `401 Unauthorized` |
| **Survey** | `/api/surveys/{survey_id}` | `DELETE` | Löschen einer Umfragedefinition (Admin, geschützt) | `204 No Content`, `401 Unauthorized`, `404 Not Found` |

### 1.2 Sicherheitsvorgaben (JWT-Token und Rollen)
* **Öffentliche Endpunkte (keine Authentifizierung erforderlich):** `GET /api/health`, `POST /api/login`, `GET /api/surveys` (mit optionaler Rolle), `POST /api/results`.
* **Geschützte Endpunkte (JWT-Token im Header `Authorization: Bearer <token>` erforderlich):** `POST /api/surveys`, `GET /api/results`, `DELETE /api/surveys/{survey_id}`.
* Bei fehlendem oder ungültigem Token antwortet der Server mit `401 Unauthorized`. Besitzt das Token nicht die Rolle `admin`, antwortet der Server mit `403 Forbidden`.
* **Prävention von Browser-Caching (Cache-Busting):** Um die Anzeige veralteter Datensätze im Dashboard zu verhindern, sendet das Backend bei `GET /api/results` den HTTP-Response-Header `Cache-Control: no-store, no-cache, must-revalidate, max-age=0`. Das Frontend hängt zusätzlich bei jedem API-Aufruf an diesen Endpunkt einen dynamischen Zeitstempel-Parameter (`?t=Zeitstempel`) als Cache-Buster an.

---

## 2. Datenmodelle und Payloads

### 2.1 Umfragedefinition (GET `/api/surveys`)
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
      "subtype": "boxes",
      "scale_min_label": "Sehr gut",
      "scale_max_label": "Ungenügend",
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
    "q3": ["prüfungsvorbereitung", "recherche"],
    "q4": "5"
  }
}
```

---

## 3. Client-Spezifikationen und State Management

### 3.1 Dynamisches UI-Rendering
Der Client generiert HTML-Formulare zur Laufzeit vollautomatisch und typgerecht auf Basis des vom Server gelieferten JSON-Objekts.
* **Typ `text`**: Generierung einer HTML-Textarea.
* **Typ `single_choice`**: Generierung von Radio-Buttons, die im Frontend als eckige Kästchen gerendert werden.
  * **Erzwingung der Single-Choice-Logik:** Das System stellt auf Clientseite strikt sicher, dass zu jedem Zeitpunkt maximal eine Option der Frage ausgewählt sein kann. Das Markieren einer anderen Option deselektiert die vorherige automatisch. Die Javascript-Logik wird separat pro Formular/Frage isoliert (z. B. durch Iteration über das jeweilige Formular/Frage-Container), sodass das Klicken einer Option nur Elemente derselben Frage deselektiert. Im finalen Antwort-Payload an den Server wird ein einzelner String-Wert übergeben.
* **Typ `multiple_choice`**: Generierung von Checkboxen, die im Frontend ebenfalls als eckige Kästchen gerendert werden.
* **Typ `rating`**: Generierung einer Bewertungsskala (Zahlen 1 bis 5).
  * **Darstellungs-Subtypen:**
    - `boxes` (Standard): Eine horizontale Reihe aus 5 eckigen Boxen (Zahlen 1 bis 5). Bei Auswahl einer Box wird diese farblich gefüllt und die Zahl in weißer Textfarbe dargestellt, damit diese gut lesbar bleibt.
    - `slider`: Ein horizontaler Schieberegler (Range-Slider) von 1 bis 5 mit einer Echtzeit-Anzeige des aktuell ausgewählten Werts darunter.
  * **Einstellbare Skalen-Beschriftung (Legende):** Die Beschriftung für den minimalen (Wert 1) und maximalen (Wert 5) Skalenendpunkt (z. B. "Sehr gut" / "Ungenügend" oder "Sehr häufig" / "Sehr selten") ist frei im Editor konfigurierbar und wird dynamisch als Legende über bzw. bei der Skala eingeblendet.
* **Einheitliches visuelles Design der Kontrollkästchen:** Sowohl für die Einzelauswahl (`single_choice`) als auch für die Mehrfachauswahl (`multiple_choice`) werden systemweit einheitlich eckige Kontrollkästchen (abgerundete Quadrate) verwendet. Eine ausgewählte Option wird durch ein klar definiertes Kreuzzeichen „X“ im Kästchen visualisiert. Runde Kontrollfelder (Radio-Kreise) oder andere Ausfüllformen sind auf der Benutzeroberfläche unzulässig.

### 3.2 Client-Zustandsmanagement (States)
Der Client durchläuft folgende Phasen:
1. **Init**: Laden und Verarbeiten der Umfragedefinition von der API.
2. **In-Progress**: Interaktive Beantwortung. Der Client erzwingt ein Route Guarding, um ein Überspringen von Fragen zu verhindern.
3. **Submitting**: Daten werden zu einem JSON-Payload aggregiert und asynchron versendet. Die UI wird während der Übertragung blockiert (Deaktivierung aller Buttons und Ladeanzeige).
4. **Completed**: Erfolgreiches Senden, Bereinigung der Session-Daten und Setzen des Cookies.

### 3.3 Speicher und Sicherheit
* **Missbrauchsschutz (Completed-Cookie):** Nach erfolgreichem Absenden wird ein Cookie namens `survey_completed_<survey_id>` mit dem Wert `saved` gesetzt (Ablaufzeit: 30 Tage, `httponly=True`, `samesite=Lax`). Bei erneutem Aufruf blockiert der Client den API-Aufruf autonom und zeigt die Danke-Seite.
* **JWT-Verarbeitung:** Das Admin-JWT wird im Authorization-Header (`Authorization: Bearer <token>`) mitgeführt. Bei einer HTTP `401 Unauthorized` Antwort des Servers wird die Client-Session sofort verworfen und ein Redirect zur Login-Seite durchgeführt.
* **Ausschließen von Client-Caching auf Seitenebene:** Die Frontend-Route `/admin` liefert in ihrer HTTP-Antwort explizit den Header `Cache-Control: no-store, no-cache, must-revalidate, max-age=0` aus, um ein Caching der gesamten HTML-Seite durch den Browser zu blockieren.

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
* Antworten vom Typ `multiple_choice` werden im JSON-Payload als Array von Option-`value`-Strings uebertragen. In der CSV-Spalte `answer` werden solche Listenantworten als JSON-Array serialisiert, damit Kommata in Optionswerten nicht als Trennzeichen fehlinterpretiert werden.

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
* **Sektion 1 (Oben - Priorität 1):** Die aggregierte Auswertung mit dem Titel "Auswertung" (ohne technische Beschreibungstexte bezüglich der serverseitigen Berechnung). Direkt neben der Überschrift befindet sich ein Dropdown-Auswahlmenü (Filter), mit dem der Administrator Statistiken und Balkendiagramme der Antworthäufigkeiten nach einer spezifischen Umfrage filtern kann. Bei Auswahl einer Umfrage aktualisieren sich die Daten sofort. Ein Button "CSV exportieren" is in dieser Sektion platziert, um den Export der aggregierten Daten zu ermöglichen.
* **Sektion 2 (Unten - Priorität 2):** Darunter folgt die Sektion für die einzelnen, eingegangenen Rohdaten aus der CSV-Datei.
* **Button-Platzierung in Sektion 2:** Der zweite "CSV exportieren"-Button für den Rohdaten-Export befindet sich auf Höhe der Überschrift dieser zweiten Sektion ("Eingegangene Ergebnisse"), rechts neben der Überschrift angeordnet. Darunter folgt die chronologische Tabelle der Einzeldaten.

### 5.2 Bereich Umfragen bearbeiten
Das Bearbeiten und Aktualisieren bestehender Umfragen wird wie folgt geregelt:
1. Der Client lädt die bestehende Struktur via `GET /api/surveys?role=admin` (oder mit entsprechender Rolle).
2. Nach Modifikation im Formular-Editor sendet der Client die aktualisierte Struktur via `POST /api/surveys` an das Backend.
3. Das Backend nimmt den Request unter JWT-Absicherung entgegen, validiert die Definition und überschreibt die bestehende JSON-Datei im Dateisystem.

### 5.3 Verhalten der CSV-Export-Schaltflächen bei aktiver Filterung
Wenn der Administrator einen Filter für eine bestimmte Umfrage-ID ausgewählt hat (Sektion 1 via Dropdown-Menü oder Sektion 2 via Klick-Filter-Buttons) und auf eine der beiden "CSV exportieren"-Schaltflächen klickt, wird die Ausführung des Downloads unterbrochen und eine Benutzerabfrage als rein textbasiertes Browser-Modal geschaltet:
* **Option A ("Nur gefilterte Umfrage exportieren"):** Lädt eine CSV-Datei herunter, die ausschließlich die Zeilen und Antworten der aktuell im Filter ausgewählten Umfrage-ID enthält.
* **Option B ("Alle Umfragen exportieren"):** Ignoriert den aktuellen Filter und lädt die komplette CSV-Datei mit sämtlichen im System existierenden Ergebnissen herunter.
* **Abbrechen-Schaltfläche:** Schließt das Modal ohne Aktion.
* **Verhalten ohne aktiven Filter:** Wenn kein Filter ausgewählt ist (Anzeige steht auf "Alle Umfragen" bzw. "Alle"), entfällt das Modal und der Button startet direkt den Download der vollständigen CSV-Datei.
* Das Modal ist in reinem, sachlichem Deutsch verfasst, verwendet korrekte deutsche Umlaute und ist absolut frei von Emojis oder Symbolen.

### 5.4 Import-Funktion für Umfragedefinitionen
Im Menüpunkt "Umfrage erstellen" (Tab 3) ist im oberen Bereich ein standardisiertes Datei-Upload-Feld mit der Beschriftung „Umfrage importieren“ vorhanden.
* **Funktionsweise:** Der Administrator lädt eine lokal gespeicherte JSON-Datei hoch. Der Client liest diese Datei ein und validiert die Struktur vollständig auf Clientseite vor der Übertragung an das Backend.
* **Validierung (Konformitätsprüfung):** Geprüft werden die Pflichtfelder `survey_id`, `title`, `role` sowie das Array `questions` (jede Frage benötigt `id`, `type`, `label`, `required` und bei Auswahlfragen ein nicht-leeres Options-Array `options` mit `value` und `text`).
* **Fehlermeldungen:** Tritt ein Validierungsfehler auf, wird der Sendevorgang blockiert. Das System zeigt dem Administrator ganz oben eine detaillierte, sachliche rote Meldung mit genauer Nennung der fehlerhaften Frage (z. B. „Fehlendes Pflichtfeld 'type' in Frage 2“).
* **Erfolgsfall:** Ist die Datei valide, wird sie automatisch per POST `/api/surveys` an den Server übertragen.

---

## 6. Strikte Format- und UI-Vorgaben: Verbot von Emojis und Umlaut-Ersatzschreibweisen
* Im gesamten Projekt – sowohl in allen Dokumentationsdateien als auch im Quellcode und der gesamten grafischen Benutzeroberfläche (UI) – ist die Verwendung von Emojis, Piktogrammen, grafischen Symbolen (z. B. SVG-Icons) oder Sonderzeichen (wie Pfeilen, Häkchen oder Warndreiecken) strengstens untersagt.
* Jegliche visuelle Kennzeichnung oder Navigation hat ausschließlich über rein sachlichen, professionellen Text zu erfolgen.
* **Strikte Umlaut-Regel (Encoding-Erzwingung):** Sämtliche Systemtexte, Bezeichnungen, Labels und Elemente der Benutzeroberfläche müssen echte deutsche Umlaute (ä, ö, ü, ß) verwenden. Jede Form von Ersatzschreibweisen (ae, oe, ue) oder fehlerhaften ASCII/ISO-Codierungen im Frontend ist technisch unzulässig.
* **Systemweites UTF-8-Erzwingungsgebot:** 
  * Das gesamte Projekt ist ausnahmslos auf UTF-8 konfiguriert. Dies gilt für alle HTML-, JavaScript-, Python- (Flask), CSV- und JSON-Dateien.
  * Beim Einlesen und Schreiben aller JSON- und CSV-Dateien im Python-Code wird explizit das Encoding UTF-8 erzwungen (z. B. `open(..., encoding='utf-8')`).
  * Sämtliche HTTP-Antworten der Flask-Anwendung liefern den korrekten Header `Content-Type: text/html; charset=utf-8` beziehungsweise `application/json; charset=utf-8` aus.
  * Jede HTML-Datei deklariert als allererstes Element im `<head>`-Bereich das Meta-Tag `<meta charset="utf-8">`.

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

---

## 8. Erweiterte Spezifikation (Version 1.5)

### 8.1 Zusätzliche Fragetypen
Das System unterstützt neben den Standardtypen zwei zusätzliche Fragetypen:
* **Typ `yes_no`**: Ja/Nein-Auswahl. Wird im Frontend für Teilnehmer als zwei beschriftete Auswahlknöpfe ("Ja" und "Nein") dargestellt. Das Antwort-Payload enthält den String "ja" oder "nein". Die statistische Auswertung im Administratorbereich zählt die Häufigkeiten beider Antwortoptionen und zeigt sie im Balkendiagramm an.
* **Typ `date`**: Datumsauswahl. Ermöglicht dem Teilnehmer die Angabe eines Datums über ein HTML5-Datumseingabefeld (`<input type="date">`). Die Validierung auf Client- und Serverseite stellt sicher, dass ein gültiges Datum eingegeben wird. Im Administrator-Dashboard werden die Datumsangaben gesammelt in einer Liste analog zu Freitextantworten dargestellt.

### 8.2 Umfrage-Vorlagen (Templates)
Im Tab "Umfrage erstellen" (Tab 3) steht eine Sektion zum Laden vordefinierter Vorlagen zur Verfügung:
* **Studentenevaluation**: Befüllt das Formular automatisch mit Fragen zur Nützlichkeit von Übungsmaterialien, der Struktur der Vorlesung, Weiterempfehlung, dem Ausfülldatum und Freitext-Anmerkungen.
* **Professorenevaluation**: Befüllt das Formular automatisch mit Fragen zu Forschungsressourcen, administrativer Unterstützung, IT-Anfragen und Infrastruktur-Anregungen.
* Das Laden einer Vorlage überschreibt nach einer Bestätigung durch den Administrator den aktuellen Zustand des Formulars.

### 8.3 Single-Page-Application-Verhalten (SPA) und Ladeanzeige
* **Lade-Indikator**: Bei jedem asynchronen Ladevorgang, insbesondere beim Nachladen einer Umfragedefinition im Dropdown des Tab "Umfrage bearbeiten", wird das globale Lade-Overlay ("Bitte warten...") angezeigt, um eine reibungslose Rückmeldung zu geben.
* **Seiten-Reload-Freies Speichern und Aktualisieren**: Alle administrativen Aktionen – wie das Speichern von Änderungen an einer Umfrage, das Erstellen oder Löschen einer Umfrage sowie das Importieren von Umfragedefinitionen – werden asynchron (via Fetch-API) ausgeführt. Das Backend speichert die geänderten Daten persistent im Dateisystem. Nach erfolgreichem Abschluss wird der Zustand der Benutzeroberfläche (Auswahl-Dropdowns, Ergebnisse, Auswertungen) per DOM-Ersatz aktualisiert, ohne dass die gesamte Seite neu geladen wird.
* **Dynamische Aktualisierung**: Die Schaltflächen "Aktualisieren" im Dashboard führen anstelle eines vollständigen Seiten-Reloads eine asynchrone Aktualisierung der Daten durch.

### 8.4 Struktur-Export im Editor
Im Tab "Umfrage bearbeiten" (Tab 2) befindet sich neben der Schaltfläche "Änderungen speichern" eine Option "Struktur exportieren". Diese generiert eine JSON-Datei mit der vollständigen Definition der aktuell geladenen Umfrage (inklusive IDs, Typen, Labels und Optionen) und startet den Browser-Download dieser Datei.

### 8.5 Teilnahme-Statistik
Am oberen Rand des Auswertungs-Tabs (Tab 4) wird ein übersichtliches Panel mit Teilnahme-Statistiken angezeigt. Dieses Panel visualisiert:
* Die Gesamtzahl aller im System eingegangenen Fragebögen.
* Die spezifische Beteiligungszahl pro definierter Umfrage.
* Bei aktiver Filterung nach einer bestimmten Umfrage werden die Statistik-Karten der übrigen Umfragen automatisch ausgeblendet.

### 8.6 Visuelle Differenzierung von Kontrollkästchen und Auswahlknöpfen
Zur Steigerung der visuellen Klarheit wird eine strikte Trennung vorgenommen:
* **Mehrfachauswahl (multiple_choice)** verwendet ein eckiges Kontrollkästchen (abgerundetes Quadrat), das bei Auswahl mit der Primärfarbe gefüllt wird und ein weißes Kreuzzeichen "X" zeigt.
* **Einzelauswahl (single_choice, yes_no)** verwendet einen runden Auswahlknopf (Radio-Circle), der bei Auswahl einen farbigen Punkt in der Mitte anzeigt.
