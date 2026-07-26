import glob, json

for f in glob.glob('backend/data/*.json'):
    try:
        data = json.load(open(f, encoding='utf-8'))
        qs = data.get('questions', [])
        print(f"--- {f} (ID: {data.get('survey_id')}) ---")
        for i, q in enumerate(qs):
            opts = [o.get('text') for o in q.get('options', [])]
            print(f"  Q{i+1} ({q.get('type')}): {q.get('label')[:30]} -> {opts}")
    except Exception as e:
        pass
