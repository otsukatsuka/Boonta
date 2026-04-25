# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Boonta v2 is a horse racing prediction system for Japanese races using JRDB data. It parses JRDB fixed-length files (BAC/KYI/SED/HJC), engineers features from JRDB indices, and runs ML predictions via AutoGluon on Modal.com. Two interfaces share the same domain code:

- **CLI** (click): data download / parse / DB ingest / training / prediction / backtest evaluation
- **Web UI** (FastAPI + SQLAlchemy/SQLite + Vite/React/TS): Bloomberg-terminal style 3 screens — DASH (race list + EV signals), RACE (entries / position chart / EV scatter / bet plan), BACKTEST (strategy matrix / equity curve / threshold sensitivity)

### Key Changes from v1

| Item | v1 | v2 |
|------|----|----|
| Data Source | netkeiba.com (HTML scraping) | JRDB (fixed-length text files) |
| Backend | FastAPI + SQLite (rule-based) | FastAPI + SQLAlchemy 2 + SQLite (WAL) + Modal/AutoGluon |
| Frontend | React (no design system) | Vite + React 18 + TS + TanStack Router/Query, Bloomberg-terminal CSS |
| ML Features | 34 (scraping-derived) | ~35 (JRDB index-based) |
| Race Forecast | Rule-based (pace.py) | JRDB forecast data + ML |
| ROI Evaluation | None | HJC payoff data, persisted backtest runs + sensitivity sweeps |

### Pre-race vs post-race data

| File | Available | Provides |
|------|-----------|----------|
| BAC | pre-race | race name / grade / distance / surface / post time / head count |
| KYI | pre-race | horse entries / odds / JRDB indices / pace forecast |
| SED | post-race | finish order / actual times (training labels + backfills race meta) |
| HJC | post-race | payouts (used by ROI / backtest) |

**Design rule**: prediction-time UI must work with BAC + KYI only. SED/HJC may be missing on race day — never assume they exist for "today". Always allow `None` for SED/HJC-derived columns.

### Inherited from v1

- Modal.com infrastructure (App "boonta-ml", Volume "boonta-models")
- AutoGluon config (binary classification, ROC-AUC, best_quality preset)
- Self-contained Modal functions pattern (no external imports, inline preprocessing)

## Development Commands

```bash
# Setup (Python — venv required, see memory/feedback_venv.md)
source .venv/bin/activate
pip3 install -e ".[dev]"

# Setup (Web)
pnpm --dir web install

# CLI — JRDB data
python cli.py download --type [BAC|KYI|SED|HJC] --date 260426
python cli.py parse    --type [BAC|KYI|SED|HJC] --date 260426
python cli.py train    --date-range 20200101 20251231 --time-limit 1800
python cli.py predict  --date 260426
python cli.py evaluate --date-range 20250101 20251231

# CLI — DB / Web UI
python cli.py db init                         # alembic upgrade + WAL
python cli.py db ingest --type BAC --date 260426
python cli.py db ingest-all --date 260426     # BAC+KYI+SED+HJC, missing skipped
python cli.py serve [--no-vite] [--port 8000] # uvicorn + (optional) vite
python cli.py backtest run --strategy all \
    --date-range 20250101 20251231 --ev-threshold 1.0

# Web — dev/build
pnpm --dir web dev          # http://localhost:5173 (proxies /api → 8000)
pnpm --dir web build
pnpm --dir web typecheck

# Quality
ruff check src/ cli.py config/
mypy src/ cli.py config/
pytest
pytest tests/test_parser/ -v
pytest -k "test_name" -v
pytest --cov=src --cov-report=html

# Modal
modal deploy src/model/functions.py
modal run src/model/functions.py::test_status
modal run src/model/functions.py::test_train
```

**Important**: Always use `best_quality` preset for AutoGluon. Do NOT use `extreme` preset.

## Architecture

### Data Pipeline

```
JRDB Server → data/raw/ (BAC/KYI/SED/HJC) → DB ingest (SQLAlchemy) ─┐
                download/         parser/        db/                  │
                                                                      ▼
                                                              data/boonta.db (SQLite WAL)
                                                              race / horse_entry / prediction
                                                              hjc_payout / backtest_*
                                                                      │
              ┌──────────────────────────────────┬───────────────────┤
              ▼                                  ▼                   ▼
   features/build_prediction_features  src/api  (FastAPI)   src/backtest/runner.py
              │                          /api/races/{key}/predict     │
              ▼                          /api/backtest/run            │
        Modal.com (AutoGluon)            ──────────┐                  │
        train_model() / predict()                  │                  │
              │                                    │                  ▼
              └────────► prediction (DB upsert) ◄──┘    backtest_run + detail + sensitivity
                                                                      │
                                            web/  (Vite/React/TS)  ◄──┘
                                            DASH / RACE / BACKTEST
```

### Source Structure (`src/`)

- **download/** - JRDB HTTP downloader with auth + ZIP/LZH extraction (BAC has its own URL pattern)
- **parser/** - Fixed-length file parser engine + BAC/KYI/SED/HJC field specs
- **features/** - Feature engineering (column definitions, derived features)
- **model/** - Modal functions (train, predict, status) + client + image
- **predict/** - Prediction runner, 展開予想 formatter, EV-based bet recommendation, ROI evaluator
- **db/** - SQLAlchemy 2.x models, session factory (WAL), ingest pipeline (KYI/SED/HJC/BAC → upsert)
- **api/** - FastAPI app, routers (system / races / predict / backtest), Pydantic schemas, JRDB code → label mapping
- **backtest/** - DB → DataFrame → `evaluate_roi` → `BacktestRun/Detail/Sensitivity` upsert + monthly equity curve

### Web (`web/`)

Vite + React 18 + TypeScript + TanStack Router (file-based) + TanStack Query. Designer's `styles.css` (oklch + JetBrains Mono) imported verbatim — do NOT migrate to Tailwind. Bet combo generation (`lib/betting.ts`) mirrors `src/predict/betting.py` so the EV-threshold slider re-computes locally without API round-trips.

### Config (`config/`)

- **settings.py** - Pydantic BaseSettings (JRDB auth, paths, Modal config). DB lives at `data/boonta.db` (derived from `project_root`)
- **alembic.ini** + **migrations/** - Schema migrations (autogenerate enabled, SQLite batch mode for ALTER)

### CLI (`cli.py`)

Click-based. Commands:
- legacy file pipeline: `download`, `parse`, `train`, `predict`, `evaluate`
- DB / web stack: `db init`, `db ingest`, `db ingest-all`, `serve`
- backtest: `backtest run`

## Data Security

**CRITICAL**: The following must NEVER be committed to git:
- `data/` directory (JRDB raw/processed files **and `data/boonta.db`**)
- `*.csv`, `*.lzh`, `*.zip` files
- `.env` file (JRDB credentials)
- `models/` directory
- `*_doc_utf8.txt` (JRDB official spec files — membership-only)
- `docs/private/` (JRDB specs and handover memos)
- `web/node_modules/`, `web/dist/`

Always verify `.gitignore` before committing. JRDB credentials go in `.env` only. JRDB official specs are stored under `docs/private/jrdb_specs/` (gitignored).

## Documentation Placement Rules

This is a **public** GitHub repository. Documentation must be split:

- **Public docs** (`docs/` directly): architecture, CLI reference, setup, development, features, Modal integration, evaluation strategies. **Do NOT include** JRDB byte-level field offsets, lengths, or repeating-structure layouts.
- **JRDB spec details** → `docs/private/jrdb_specs/` (gitignored). Includes the official `*_doc_utf8.txt` files and the annotated `jrdb_fields_reference.md`.
- **Handover documents** (containing personal bet amounts/payoffs, in-progress internal state, uncommitted-work logs) → `docs/private/handover/` (gitignored).
- **Never create new `.md` files at the repository root** other than `README.md` and `CLAUDE.md`. Anything else goes under `docs/` (public) or `docs/private/` (private).

Background: prior to 2026-04-25, JRDB spec files and handover docs were committed at the repo root and had to be purged from git history. Avoid recreating that situation.

## Parser Design

JRDB uses CP932-encoded fixed-length records. All record-length constants include the trailing CRLF (e.g. BAC body 182B + CRLF 2B = `RECORD_LENGTH = 184`). Mismatching this drifts every field one record at a time and silently produces garbage `race_key`s.

- **BAC** (番組データ): pre-race race program — race name / grade / distance / surface / post time / head count
- **KYI** (競走馬データ): pre-race horse entries, JRDB indices, pace forecast
- **SED** (成績データ): post-race results, actual times/indices (training labels + race-meta backfill)
- **HJC** (払戻データ): post-race payoffs (repeating structures, stored as raw JSON in `hjc_payout.raw`)

Field specs use 1-based byte offsets (matching JRDB docs). Parser converts to 0-based.

Race key structure: `場コード(2) + 年(2) + 回(1) + 日(1,hex) + R(2)` = 8 chars. The "year" digit pair is 下2桁 (cannot be reversed to a calendar date) and "日" is 開催日連番 (1日目/2日目...) **not** day-of-month — keep `held_on` as a separate `DATE` column derived from the filename (`KYI260426.txt` → 2026-04-26, YY < 70 → 20YY).

`ingest_*` validates `race_key` (venue 01-10, R 1-12) and drops malformed rows so a bad RECORD_LENGTH cannot leave orphan races in the DB.

JRDB BAC has its own URL pattern: `https://jrdb.com/member/data/Bac/BAC{YYMMDD}.lzh` (no year subdirectory, https). HJC also uses its own pattern: `https://jrdb.com/member/datazip/Hjc/20YY/HJC{YYMMDD}.zip` (https + `jrdb.com` origin, `.zip` — JRDB stopped publishing `.lzh` for HJC). KYI/SED live under `http://www.jrdb.com/member/datazip/{Type}/20YY/{TYPE}{YYMMDD}.zip`.

Reference docs (private, gitignored under `docs/private/jrdb_specs/`):
- `kyi_doc_utf8.txt` - KYI field specification
- `sed_doc_utf8.txt` - SED field specification
- `hjcdata_doc_utf8.txt` - HJC field specification
- `jrdb_fields_reference.md` - Annotated subset used by ML features
- (BAC spec was reconstructed from the public `absoishi/jrdb` GitHub repo + verified against real downloaded files)

## Feature Engineering

6 categories, ~35 features total:

1. **展開コア** (KYI): pace_forecast, mid/late3f/goal position/gap/io, tenkai_symbol
2. **スピード指標** (KYI/SED): ten/pace/agari/position index, IDM
3. **馬・厩舎・騎手指数** (KYI): jockey/info/overall/training/stable index
4. **適性・リスク** (KYI): running_style, distance_aptitude, heavy_track, start/gate_miss, upset
5. **レース条件**: horse_number, waku, odds, popularity, weight_carried
6. **派生フィーチャー**: speed_balance, position_delta, io_shift, log_odds, risk_score

**Design rule**: Training features use only KYI-derived data (available at prediction time). SED provides labels (is_place = 着順 <= 3) and anomaly filters only.

## Modal Integration

Self-contained functions in `src/model/functions.py` (no imports from `src/`):

| Function | Purpose | Resources |
|----------|---------|-----------|
| `train_model()` | AutoGluon training | 8GB, CPU 4.0, 7200s timeout |
| `predict()` | is_place probability | 4GB, 60s timeout |
| `get_model_status()` | Model state check | 30s timeout |
| `get_feature_importance()` | Feature importance | 4GB, 60s timeout |

- App name: `boonta-ml`, Volume: `boonta-models`, Model: `jrdb_predictor`
- Image: debian_slim + Python 3.11 + AutoGluon 1.4.0
- Client (`src/model/client.py`): Synchronous (CLI-based, not async)
- Preprocessing logic is defined inline in functions.py
- API endpoint `POST /api/races/{race_key}/predict` uses Modal synchronously (~5–20s incl. cold start), upserts `prediction` rows with `model_version = "jrdb_predictor@<trained_at>"` so re-prediction is idempotent

## Web UI

3 screens, Bloomberg-terminal aesthetic. Designer's prototype lives at `docs/ui/boonta/` (HTML/JSX/CSS) — these are the source of truth for visual decisions; never invent UI from scratch.

- **DASH** (`/`): date picker (URL search param `?date=YYYY-MM-DD`) → race table + EV signals + pace distribution. RUN button calls predict-batch.
- **RACE** (`/race/$raceKey`): race header / entries+ML+EV table / corner position chart / EV scatter (iso EV lines) / bet plan card. PREDICT button re-runs Modal for one race.
- **BACKTEST** (`/backtest`): strategy matrix (6 strategies, sparkline equity) / EquityCurve / Threshold Sensitivity / SummaryStats. RUN button kicks server-side recalc.
- **TweaksPanel**: floating EV-threshold slider (0.80–1.50 step 0.05). UI state only (localStorage), no API call — bet combos and ★ markers re-derive client-side.

API responses use snake_case throughout. Frontend keeps short JSX-style names (`n`, `w`, `prob`) only inside design components; the wire format stays explicit. EV is computed both server-side (for persistence) and client-side (for slider responsiveness) — formulas must stay in sync: `ev_tan = (prob/3) * odds`, `ev_fuku = prob * fukusho_odds`.

JRDB code → label conversion (e.g. surface `"2"` → `"ダ"`, weather `"1"` → `"晴"`, grade `"2"` → `"G2"`) happens at the API serialization boundary in `src/api/labels.py` — DB stores raw codes so the mapping can be revised without re-ingesting. SED's `馬場状態` is 2 chars (芝state + ダstate); split based on `surface` before lookup.

## Testing

```
tests/
├── conftest.py
├── fixtures/           # Binary JRDB record samples (.bin)
├── test_parser/        # Parser engine + KYI/SED/HJC field tests
├── test_features/      # Feature engineering tests
├── test_model/         # Modal preprocessing tests (AutoGluon mocked)
└── test_predict/       # Prediction runner + 展開予想 + ROI tests
```

- Test fixtures use binary `.bin` files (spec-compliant dummy records), NOT CSV
- Modal/AutoGluon mocked in tests
- No real JRDB data needed for tests

## Database Design Rules

- All tables use surrogate `id INTEGER PRIMARY KEY AUTOINCREMENT`. Domain natural keys (`race_key`, `(race_id, horse_number)`, `(horse_entry_id, model_version)`) are `UNIQUE` constraints, **never** PKs. FKs reference internal `id`. Natural keys stay at the API boundary only.
- SQLite must use WAL (`PRAGMA journal_mode=WAL`) to avoid `database is locked` when API reads while CLI/backtest writes. Set in `src/db/session.py` on every connect.
- Predictions are upserted on `(horse_entry_id, model_version)`; re-predicting the same race overwrites in place rather than producing duplicates.
- Backtest runs are upserted on `(strategy, date_from, date_to, ev_threshold, model_version)`; old runs are deleted before new insert (CASCADE drops detail/sensitivity rows).
- `backtest_detail.held_on` denormalizes `race.held_on` so monthly equity-curve aggregation needs no JOIN.

## Code Style

- **ruff**: line-length 100, target Python 3.10
- **mypy**: Python 3.10, strict return type warnings
- **preset**: AutoGluon `best_quality` only. `extreme` is FORBIDDEN
- **TypeScript** (`web/`): strict mode, ESM only, `pnpm typecheck` must pass before commit. Designer's `styles.css` is imported verbatim — do not refactor into Tailwind / CSS modules.

## Related Documents

Public docs (under `docs/`):
- `docs/ARCHITECTURE.md` - System design, data pipeline, module responsibilities
- `docs/CLI.md` - Full CLI command reference
- `docs/SETUP.md` - Environment setup
- `docs/DEVELOPMENT.md` - Dev workflow, testing, coding conventions
- `docs/FEATURES.md` - Feature engineering (~35 features in 6 categories)
- `docs/MODAL.md` - Modal integration, function specs, ops tips
- `docs/EVALUATION.md` - ROI / EV strategies and backtesting
- `docs/ui/boonta/` - Designer's React/HTML/CSS prototype for the Web UI (read before changing visual layout)

Private docs (gitignored under `docs/private/`):
- `docs/private/jrdb_specs/` - JRDB official spec files + ML field reference
- `docs/private/handover/` - Internal handover notes (E2E_HANDOVER, BACKTEST_HANDOVER)
