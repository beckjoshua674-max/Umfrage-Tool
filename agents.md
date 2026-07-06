Richtlinien für die Zusammenarbeit der KI-Agenten (Ask Alma Umfrage-Tool)

1. Systemkontext
Du arbeitest als KI-Entwicklungsassistent an einem Projekt für das Universitätsmodul "Verteilte Systeme". Das Projekt ist ein Umfrage-Tool zur Evaluierung der KI "Ask Alma".

Das Repository wird gemeinsam von zwei menschlichen Entwicklern verwaltet, die zwei verschiedene KI-Agenten nutzen: Antigravity (zuständig für das Frontend) und Codex (zuständig für das Backend).

2. Rollen & Grenzen der Agenten
Antigravity (Frontend-Agent): Ausschließlich zuständig für das Verzeichnis /frontend und das UI/UX. Der Tech-Stack ist auf Python, HTML und CSS beschränkt. JavaScript ist grundsätzlich verboten – mit einer einzigen Ausnahme: Im Admin-Bereich darf JavaScript ausschließlich zur Einbindung des **SurveyJS Creators** via CDN genutzt werden. Die primäre Corporate-Design-Farbe ist **#2160a6** (Hochschule Kehl).

Codex (Backend-Agent): Ausschließlich zuständig für die serverseitige Architektur, Datenlogik und das Routing. Der gesamte Backend-Code muss ausnahmslos in Python geschrieben werden.

Strikte Abgrenzung: Ändere KEINE Dateien außerhalb deines zugewiesenen Bereichs, es sei denn, du wirst ausdrücklich vom menschlichen Nutzer dazu aufgefordert.

3. Workflow-Regeln
Immer den Kontext lesen: Bevor du neuen Code generierst, lies immer diese agents.md und die requirements.md, um den aktuellen Projektstatus und die Architekturregeln zu verstehen.

Strikter Python- & HTML/CSS-Stack: Die gesamte Anwendung muss mit Python entwickelt werden. Datenaustausch und Interaktivität müssen über Python abgewickelt werden (z. B. serverseitiges Rendering über Templates wie Jinja2 oder standardmäßige HTML-Formularübermittlungen). Das Schreiben oder Generieren von JavaScript ist strengstens untersagt – **Ausnahme:** Das Admin-Template `admin_builder.html` darf JavaScript ausschließlich für den SurveyJS Creator (CDN-Einbindung) und den zugehörigen API-Aufruf (`POST /api/surveys`) verwenden.

Keine destruktiven Überschreibungen: Wenn du die Datenstruktur oder die Rendering-Logik ändern musst, kommuniziere die erforderlichen Änderungen in den Code-Kommentaren, damit der andere Agent seine Arbeit entsprechend anpassen kann.

Schnittstellen-Dokumentation: Wenn eine neue Schnittstelle (z. B. eine neue Route oder ein Datenübergabepunkt) angelegt oder benötigt wird, muss dies zwingend als neuer Punkt in der requirements.md dokumentiert werden. Dabei muss klar definiert werden, welche Daten in welcher Form (z. B. Datenstruktur, Parameter, Datentypen) übergeben werden und was als Antwort erwartet bzw. empfangen wird. Dadurch weiß der andere Agent exakt, worauf er zugreifen oder was er erstellen muss.

Automatische Synchronisation der requirements.md: Jede Änderung an der Architektur, an API-Endpunkten, an Rollen/Berechtigungen, an Datendateien oder an Sicherheitsregeln (z. B. welche Routen ein Token erfordern) muss **sofort und ohne Rückfrage** in der `requirements.md` nachgepflegt werden – noch bevor oder zeitgleich mit der eigentlichen Code-Änderung. Dies gilt für beide Agenten (Antigravity und Codex). Ziel ist, dass die `requirements.md` jederzeit den vollständigen und aktuellen Stand aller Schnittstellen, Rollen, Dateipfade, Test-Credentials und Zugriffsregeln widerspiegelt, sodass der jeweils andere Agent ohne zusätzliche Rückfragen arbeiten kann.

Deutsche Kommentare: Alle Code-Kommentare, Erklärungen und Dokumentationen innerhalb des Quellcodes müssen zwingend auf Deutsch verfasst werden.

Zustandsdokumentation vor jeder Implementierung (Pflicht): Bevor eine neue Funktion implementiert oder eine bestehende geändert wird, müssen alle betroffenen Zustände (States) vollständig definiert und in der requirements.md eingetragen sein – niemals nachträglich. Dies umfasst: welche Session-Variablen angelegt/geändert/gelöscht werden, welche Cookies gesetzt werden (Name, Lebensdauer, Flags), welche Daten dauerhaft im Backend gespeichert werden, welche temporären UI-Zustände im Browser entstehen und welche Fehlerzustände auftreten können (inkl. HTTP-Statuscode und System-Reaktion). Diese Regel gilt für beide Agenten (Antigravity und Codex) und für jeden Änderungstyp (Feature, Bugfix, Refactoring). Vgl. requirements.md Kap. 13.


4. Git- & Commit-Standards
Wenn du dem menschlichen Nutzer Commit-Nachrichten vorschlägst, verwende strikt das "Conventional Commits"-Format auf Deutsch oder Englisch (z. B. feat(frontend): python rendering logik hinzugefuegt, fix(design): primaerfarbe auf #334aff aktualisiert, refactor(backend): python routen umstrukturiert).

5. Aktueller Projektstatus
Frontend: UI im HS-Kehl-Design (Farbe #2160a6), Schritt-für-Schritt-Umfrageführung, Admin-Dashboard mit Login (admin/admin123), SurveyJS-Builder-Seite implementiert.

Backend: Grundlegende Endpunkte (GET /api/health, GET /api/survey, POST /api/results) funktionieren. Ausstehend: POST /api/login, POST /api/surveys, DELETE /api/surveys/{survey_id}, rollenbasierte Survey-Auslieferung, GET /api/results.