Richtlinien für die Zusammenarbeit der KI-Agenten (Ask Alma Umfrage-Tool)

1. Systemkontext
Dieses Projekt dient dem Universitätsmodul "Verteilte Systeme". Es handelt sich um ein Umfrage-Tool zur Evaluierung der KI "Ask Alma". Das Repository wird gemeinschaftlich von zwei Entwicklern verwaltet, die zwei unterschiedliche KI-Agenten einsetzen: Antigravity (zuständig für das Frontend) und Codex (zuständig für das Backend).

2. Rollen und Grenzen der Agenten
* Antigravity (Frontend-Agent): Ausschließlich zuständig für das Verzeichnis /frontend und das UI/UX. Der Tech-Stack ist auf Python, HTML und CSS beschränkt. JavaScript ist grundsätzlich unzulässig – mit der Ausnahme des Admin-Bereichs zur Einbindung des SurveyJS Creators via CDN. Die primäre Corporate-Design-Farbe lautet #2160a6 (Hochschule Kehl).
* Codex (Backend-Agent): Ausschließlich zuständig für die serverseitige Architektur, Datenlogik und das Routing. Der Backend-Code wird vollständig in Python implementiert.
* Strikte Abgrenzung: Keine Modifikationen an Dateien außerhalb des jeweils zugewiesenen Bereichs, es sei denn, es liegt eine explizite Anweisung des Nutzers vor.

3. Workflow-Regeln
* Kontextprüfung: Vor der Generierung von Code sind diese agents.md sowie die requirements.md einzulesen, um den aktuellen Systemzustand und die Architekturregeln zu verstehen.
* Strikter Python- und HTML/CSS-Stack: Datenaustausch und Interaktivität erfolgen über Python (z. B. serverseitiges Rendering über Jinja2-Templates oder standardmäßige HTML-Formularübermittlungen). Das Generieren von JavaScript ist unzulässig (Ausnahme: Das Admin-Template admin_builder.html für den SurveyJS Creator und den API-Aufruf POST /api/surveys).
* Vermeidung destruktiver Überschreibungen: Änderungen an der Datenstruktur oder der Rendering-Logik sind in Code-Kommentaren zu kommunizieren, um eine Abstimmung zu ermöglichen.
* Schnittstellen-Dokumentation: Jede neue Schnittstelle muss in der requirements.md dokumentiert werden. Dabei sind übergebene Parameter, Datentypen und erwartete Antworten klar zu definieren.
* Automatische Synchronisation der requirements.md: Änderungen an der Architektur, Endpunkten, Berechtigungen, Datendateien oder Sicherheitsregeln sind unverzüglich in der requirements.md zu dokumentieren (vor oder zeitgleich mit der Implementierung).
* Deutsche Kommentare: Alle Kommentare, Erklärungen und Dokumentationen im Quellcode sind in deutscher Sprache zu verfassen.
* Zustandsdokumentation vor der Implementierung: Vor jeder Änderung sind die betroffenen Zustände (Session-Variablen, Cookies, Backend-Daten, flüchtige UI-Zustände, Fehlerzustände) in der requirements.md zu definieren.
* Abhängigkeitsverwaltung: Python-Abhängigkeiten werden standardisiert in der `requirements.txt` gepflegt und über das Paketverwaltungstool `pip` installiert (`pip install -r requirements.txt`). Diese Datei ist essenziell für die saubere Umgebungskonfiguration.

4. Git- und Commit-Standards
Commit-Nachrichten sind gemäß dem "Conventional Commits"-Format in deutscher oder englischer Sprache zu formulieren (z. B. feat(frontend): python rendering logik hinzugefügt, fix(design): primärfarbe auf #334aff aktualisiert, refactor(backend): python routen umstrukturiert).

5. Aktueller Projektstatus
* Frontend: UI im HS-Kehl-Design (Farbe #2160a6), Schritt-für-Schritt-Umfrageführung, Admin-Dashboard mit Login (admin/admin123), automatischem Logout bei URL-Wechsel und eingebettetem Creator sowie angepasstem CSV-Export-Layout implementiert.
* Backend: API-Endpunkte (GET /api/health, GET /api/survey, POST /api/results, POST /api/login, POST /api/surveys, GET /api/results, DELETE /api/surveys/{survey_id}) vollständig implementiert und getestet.