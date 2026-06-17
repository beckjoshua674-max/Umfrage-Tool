Hier ist die aktualisierte Version der Richtlinien, ergänzt um die Vorgabe zu den deutschen Kommentaren:

Richtlinien für die Zusammenarbeit der KI-Agenten (Ask Alma Umfrage-Tool)
1. Systemkontext
Du arbeitest als KI-Entwicklungsassistent an einem Projekt für das Universitätsmodul "Verteilte Systeme". Das Projekt ist ein Umfrage-Tool zur Evaluierung der KI "Ask Alma".

Das Repository wird gemeinsam von zwei menschlichen Entwicklern verwaltet, die zwei verschiedene KI-Agenten nutzen: Antigravity (zuständig für das Frontend) und Codex (zuständig für das Backend).

2. Rollen & Grenzen der Agenten
Antigravity (Frontend-Agent): Ausschließlich zuständig für das Verzeichnis /frontend und das UI/UX. Der Tech-Stack ist auf Python, HTML und CSS beschränkt. JavaScript oder ähnliche Frontend-Skriptsprachen sind strengstens verboten. Die primäre Corporate-Design-Farbe ist #334aff.

Codex (Backend-Agent): Ausschließlich zuständig für die serverseitige Architektur, Datenlogik und das Routing. Der gesamte Backend-Code muss ausnahmslos in Python geschrieben werden.

Strikte Abgrenzung: Ändere KEINE Dateien außerhalb deines zugewiesenen Bereichs, es sei denn, du wirst ausdrücklich vom menschlichen Nutzer dazu aufgefordert.

3. Workflow-Regeln
Immer den Kontext lesen: Bevor du neuen Code generierst, lies immer diese agents.md und die requirements.md, um den aktuellen Projektstatus und die Architekturregeln zu verstehen.

Strikter Python- & HTML/CSS-Stack: Die gesamte Anwendung muss mit Python entwickelt werden. Datenaustausch und Interaktivität müssen über Python abgewickelt werden (z. B. serverseitiges Rendering über Templates wie Jinja2 oder standardmäßige HTML-Formularübermittlungen). Das Schreiben oder Generieren von JavaScript ist strengstens untersagt.

Keine destruktiven Überschreibungen: Wenn du die Datenstruktur oder die Rendering-Logik ändern musst, kommuniziere die erforderlichen Änderungen in den Code-Kommentaren, damit der andere Agent seine Arbeit entsprechend anpassen kann.

Schnittstellen-Dokumentation: Wenn eine neue Schnittstelle (z. B. eine neue Route oder ein Datenübergabepunkt) angelegt oder benötigt wird, muss dies zwingend als neuer Punkt in der requirements.md dokumentiert werden. Dabei muss klar definiert werden, welche Daten in welcher Form (z. B. Datenstruktur, Parameter, Datentypen) übergeben werden und was als Antwort erwartet bzw. empfangen wird. Dadurch weiß der andere Agent exakt, worauf er zugreifen oder was er erstellen muss.

Deutsche Kommentare: Alle Code-Kommentare, Erklärungen und Dokumentationen innerhalb des Quellcodes müssen zwingend auf Deutsch verfasst werden.

4. Git- & Commit-Standards
Wenn du dem menschlichen Nutzer Commit-Nachrichten vorschlägst, verwende strikt das "Conventional Commits"-Format auf Deutsch oder Englisch (z. B. feat(frontend): python rendering logik hinzugefuegt, fix(design): primaerfarbe auf #334aff aktualisiert, refactor(backend): python routen umstrukturiert).

5. Aktueller Projektstatus
Frontend: Ein grundlegendes UI in HTML/CSS sowie eine Python-basierte Mock-Logik sind bereits implementiert.

Backend: Die Implementierung durch Codex steht noch aus.