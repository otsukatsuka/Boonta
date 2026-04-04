---
name: predict-race
description: Register a race from netkeiba and run ML prediction. Use for upcoming race prediction workflow.
argument-hint: [netkeiba_race_id]
disable-model-invocation: true
---

## Race Prediction Workflow

Predict an upcoming race using the Boonta ML pipeline. Argument `$ARGUMENTS` is the netkeiba race ID (format: YYYYVVKKDDNN).

### Prerequisites
- Backend running (`uvicorn app.main:app --reload`)
- Modal model trained (`curl http://localhost:8000/api/model/status` to check)

### Steps

1. **Register the race** from netkeiba (creates race + entries + odds in DB):
```bash
curl -X POST http://localhost:8000/api/fetch/register \
  -H "Content-Type: application/json" \
  -d '{"netkeiba_race_id": "$ARGUMENTS", "fetch_odds": true}'
```

2. **Fetch running styles** (required for pace prediction). Note the DB race ID from step 1:
```bash
curl -X POST http://localhost:8000/api/fetch/running-styles/{db_race_id} \
  -H "Content-Type: application/json" \
  -d '{"netkeiba_race_id": "$ARGUMENTS"}'
```

3. **Run prediction**:
```bash
curl -X POST http://localhost:8000/api/predictions/{db_race_id}
```

4. **Show results** to the user: ranked horses, pace prediction, bet recommendations.

### Important Notes
- Always activate venv: `source .venv/bin/activate`
- Running styles use AJAX fetch from netkeiba horse pages (column index 25 for corner positions)
- If running styles all show VERSATILE, check netkeiba HTML structure may have changed
- DB race ID (integer) is different from netkeiba race ID (string)
- Check `GET /api/races` to find the DB race ID after registration
