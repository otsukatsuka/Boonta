---
name: collect-training-data
description: Collect G1 race training data from netkeiba for ML model. Use when adding new year's race data.
argument-hint: [year_start] [year_end]
disable-model-invocation: true
---

## Training Data Collection Workflow

Collect historical G1 race data from netkeiba to expand the ML training dataset. Arguments: `$0` = start year, `$1` = end year (optional, defaults to start year).

### Prerequisites
- Backend venv activated: `source .venv/bin/activate`
- Working directory: `backend/`

### Steps

1. **Fetch race IDs** from netkeiba for the target years:
```bash
python scripts/fetch_grade_race_ids.py --grade G1 --years $ARGUMENTS --output data/g1_race_ids_new.json
```

2. **Review fetched race IDs** — check the JSON output:
   - Remove obstacle races (JGI: 中山大障害, 中山グランドジャンプ) as they are jump races
   - Verify race count (typically 24 flat G1 races per year)

3. **Add race IDs** to `backend/scripts/collect_training_data.py`:
   - Add new IDs to the `KNOWN_G1_RACE_IDS` list with comments (race name + year)
   - Insert after the latest existing year's block

4. **Run data collection** (30-60 min due to netkeiba scraping delays):
```bash
python scripts/collect_training_data.py --grade G1 --with-history
```
   - This creates `data/training/g1_races_hist.csv` (with `--with-history` suffix)
   - The `--with-history` flag adds horse past performance features (win_rate, place_rate, etc.)

5. **Copy hist file to main training file**:
```bash
cat data/training/g1_races_hist.csv >| data/training/g1_races.csv
```
   - The model training reads from `g1_races.csv`

6. **Verify** row count increased:
```bash
wc -l data/training/g1_races.csv
```

### Important Notes
- Netkeiba race ID format: `YYYYVVKKDDNN` (Year/Venue/開催回/日目/Race#)
- `--with-history` outputs to `g1_races_hist.csv`, NOT `g1_races.csv` — copy is required
- Script rewrites the entire CSV (not append), so existing data is preserved
- Expect ~14-18 entries per G1 race (number of horses)
- The `last_3f`, `best_last_3f`, `avg_last_3f_hist` columns may be empty for some races — AutoGluon handles this
