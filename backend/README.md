# Backend - Ask Alma Umfrage-Tool

Python/Flask-Server fuer die API des Umfrage-Tools.

## Start

```powershell
cd backend
python app.py
```

Der Server laeuft standardmaessig auf `http://localhost:8000`.

## Datenablage

- `mock-data/survey-questions.json`: zentrale Umfragedefinition, ausgeliefert ueber `GET /api/survey`
- `data/results/*.json`: gespeicherte Umfrageantworten, eine Datei pro Einreichung
