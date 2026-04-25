# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Boonta v2 is a horse racing prediction system for Japanese races using JRDB data. It parses JRDB fixed-length files (KYI/SED/HJC), engineers features from JRDB indices, and runs ML predictions via AutoGluon on Modal.com. The interface is a CLI pipeline (click), replacing the v1 FastAPI + React architecture.

### Key Changes from v1

| Item | v1 | v2 |
|------|----|----|
| Data Source | netkeiba.com (HTML scraping) | JRDB (fixed-length text files) |
| Architecture | FastAPI + React + SQLite | Python CLI pipeline |
| ML Features | 34 (scraping-derived) | ~35 (JRDB index-based) |
| Race Forecast | Rule-based (pace.py) | JRDB forecast data + ML |
| Interface | Web app + Docker | CLI + Modal.com |
| ROI Evaluation | None | HJC payoff data |

### Inherited from v1

- Modal.com infrastructure (App "boonta-ml", Volume "boonta-models")
- AutoGluon config (binary classification, ROC-AUC, best_quality preset)
- Self-contained Modal functions pattern (no external imports, inline preprocessing)

## Development Commands

```bash
# Setup
pip install -e ".[dev]"

# CLI
python cli.py download --type KYI --date 2026-04-05
python cli.py parse --type KYI --date 2026-04-05
python cli.py train --date-range 2020-01-01 2025-12-31 --time-limit 1800
python cli.py predict --date 2026-04-05
python cli.py evaluate --date-range 2025-01-01 2025-12-31

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
JRDB Server → data/raw/ (KYI/SED/HJC) → data/processed/ (CSV) → Features DataFrame
                download/         parser/              features/
                                                          │
                                                    ┌─────┘
                                                    ▼
                                              Modal.com (AutoGluon)
                                              train_model() / predict()
                                                    │
                                                    ▼
                                              展開予想 Output + ROI Evaluation
```

### Source Structure (`src/`)

- **download/** - JRDB HTTP downloader with auth + ZIP/LZH extraction
- **parser/** - Fixed-length file parser engine + KYI/SED/HJC field specs
- **features/** - Feature engineering (column definitions, derived features)
- **model/** - Modal functions (train, predict, status) + client + image
- **predict/** - Prediction runner, 展開予想 formatter, ROI evaluator

### Config (`config/`)

- **settings.py** - Pydantic BaseSettings (JRDB auth, paths, Modal config)

### CLI (`cli.py`)

Click-based CLI with commands: download, parse, train, predict, evaluate

## Data Security

**CRITICAL**: The following must NEVER be committed to git:
- `data/` directory (JRDB raw/processed files)
- `*.csv`, `*.lzh`, `*.zip` files
- `.env` file (JRDB credentials)
- `models/` directory
- `*_doc_utf8.txt` (JRDB official spec files — membership-only)
- `docs/private/` (JRDB specs and handover memos)

Always verify `.gitignore` before committing. JRDB credentials go in `.env` only. JRDB official specs are stored under `docs/private/jrdb_specs/` (gitignored).

## Documentation Placement Rules

This is a **public** GitHub repository. Documentation must be split:

- **Public docs** (`docs/` directly): architecture, CLI reference, setup, development, features, Modal integration, evaluation strategies. **Do NOT include** JRDB byte-level field offsets, lengths, or repeating-structure layouts.
- **JRDB spec details** → `docs/private/jrdb_specs/` (gitignored). Includes the official `*_doc_utf8.txt` files and the annotated `jrdb_fields_reference.md`.
- **Handover documents** (containing personal bet amounts/payoffs, in-progress internal state, uncommitted-work logs) → `docs/private/handover/` (gitignored).
- **Never create new `.md` files at the repository root** other than `README.md` and `CLAUDE.md`. Anything else goes under `docs/` (public) or `docs/private/` (private).

Background: prior to 2026-04-25, JRDB spec files and handover docs were committed at the repo root and had to be purged from git history. Avoid recreating that situation.

## Parser Design

JRDB uses CP932-encoded fixed-length records:
- **KYI** (競走馬データ): 1024 bytes/record - horse data, JRDB indices, forecast
- **SED** (成績データ): 376 bytes/record - race results, actual times/indices
- **HJC** (払戻データ): 444 bytes/record - payoff data with repeating structures

Field specs use 1-based byte offsets (matching JRDB docs). Parser converts to 0-based.

Race key structure: `場コード(2) + 年(2) + 回(1) + 日(1,hex) + R(2)` = 8 chars

Reference docs (private, gitignored under `docs/private/jrdb_specs/`):
- `kyi_doc_utf8.txt` - KYI field specification
- `sed_doc_utf8.txt` - SED field specification
- `hjcdata_doc_utf8.txt` - HJC field specification
- `jrdb_fields_reference.md` - Annotated subset used by ML features

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

## Code Style

- **ruff**: line-length 100, target Python 3.10
- **mypy**: Python 3.10, strict return type warnings
- **preset**: AutoGluon `best_quality` only. `extreme` is FORBIDDEN

## Related Documents

Public docs (under `docs/`):
- `docs/ARCHITECTURE.md` - System design, data pipeline, module responsibilities
- `docs/CLI.md` - Full CLI command reference
- `docs/SETUP.md` - Environment setup
- `docs/DEVELOPMENT.md` - Dev workflow, testing, coding conventions
- `docs/FEATURES.md` - Feature engineering (~35 features in 6 categories)
- `docs/MODAL.md` - Modal integration, function specs, ops tips
- `docs/EVALUATION.md` - ROI / EV strategies and backtesting

Private docs (gitignored under `docs/private/`):
- `docs/private/jrdb_specs/` - JRDB official spec files + ML field reference
- `docs/private/handover/` - Internal handover notes (E2E_HANDOVER, BACKTEST_HANDOVER)
