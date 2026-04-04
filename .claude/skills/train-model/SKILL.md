---
name: train-model
description: Train or retrain the ML prediction model on Modal. Use after updating training data.
disable-model-invocation: true
---

## Model Training Workflow

Train the AutoGluon ML model on Modal.com for race predictions.

### Prerequisites
- Backend running (`uvicorn app.main:app --reload`)
- Training data up to date (`backend/data/training/g1_races.csv`)
- Modal authenticated (`modal token new` if expired)
- Modal app deployed (`modal deploy modal_app/functions.py`)

### Steps

1. **Check current model status**:
```bash
curl http://localhost:8000/api/model/status
```

2. **Deploy Modal app** (required after any code changes to `modal_app/`):
```bash
cd backend && source .venv/bin/activate
modal deploy modal_app/functions.py
```

3. **Start training** via API:
```bash
curl -X POST http://localhost:8000/api/model/train \
  -H "Content-Type: application/json" \
  -d '{"time_limit": 1800}'
```
   - Returns a `call_id` for status tracking
   - Takes ~30 minutes with `best_quality` preset

4. **Monitor progress**:
   - Via API: `curl http://localhost:8000/api/model/training-status/{call_id}`
   - Via Modal Dashboard: `modal dashboard` (opens browser with real-time logs)

5. **Verify completion**:
```bash
curl http://localhost:8000/api/model/status
```
   - Check `is_trained: true` and `metrics.roc_auc` score

### Critical Notes

**DO NOT use `extreme` preset on CPU** — it tries to train Mitra/TabPFN/TabDPT/TabICL models that either:
- Require GPU (Mitra: will run but takes hours on CPU)
- Require missing dependencies (TabPFN, TabDPT, TabICL: ImportError)

The code auto-selects `best_quality` which uses LightGBM/CatBoost/XGBoost/NN/RF — fast and effective on CPU.

**Always redeploy before training** if you changed `modal_app/functions.py`. Otherwise the old code runs on Modal.

### Presets Reference
| Preset | Models | Time | Use Case |
|--------|--------|------|----------|
| `medium_quality` | GBM, CAT, XGB | 5-10 min | Quick testing |
| `best_quality` | GBM, CAT, XGB, NN, RF + stacking | 20-30 min | Production |
| `extreme` | Above + Mitra, TabPFN, etc. | Hours+ | **Avoid on CPU** |
