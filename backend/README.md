# Backend - Ask Alma Umfrage-Tool

Python-Server fuer die API des Umfrage-Tools.

## Start

```powershell
cd backend
python app.py
```

Der Server laeuft standardmaessig auf `http://localhost:8000`.

## Datenablage

- `data/survey_student.json`: Fragenkatalog fuer `GET /api/survey?role=student`
- `data/survey_professor.json`: Fragenkatalog fuer `GET /api/survey?role=professor`
- `data/results/*.json`: gespeicherte Umfrageantworten, eine Datei pro Einreichung
