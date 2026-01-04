# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Boonta is a horse racing prediction AI service for Japanese G1 races. It uses machine learning (AutoGluon 1.5.0 on Modal.com) to predict race outcomes based on historical data, running styles, jockey statistics, and workout information.

## Development Commands

### Frontend (React + Vite + TypeScript)

```bash
cd frontend
npm run dev      # Start dev server at http://localhost:5173
npm run build    # TypeScript check + production build
npm run lint     # ESLint check
npm run preview  # Preview production build
```

### Backend (Python + FastAPI)

```bash
cd backend
pip install -r requirements.txt        # Install dependencies
pip install -e ".[dev]"                 # Install with dev dependencies
uvicorn app.main:app --reload          # Start dev server at http://localhost:8000

# Linting and testing
ruff check app/                         # Lint Python code
mypy app/                               # Type checking
pytest                                  # Run tests
pytest tests/path/to/test.py -v        # Run single test file
pytest -k "test_name" -v               # Run specific test
```

### Modal (ML Environment)

```bash
cd backend

# Authentication (first time only)
modal token new

# Deploy Modal app
modal deploy modal_app/functions.py

# Test locally before deploying
modal run modal_app/functions.py::test_status    # Check model status
modal run modal_app/functions.py::test_train     # Run test training

# Upload existing local model to Modal Volume
modal run scripts/upload_model_to_modal.py
```

### Docker

```bash
docker compose up --build              # Build and start all services
docker compose up -d                   # Start in background
docker compose down                    # Stop all services
docker compose logs -f backend         # View backend logs
docker compose logs -f frontend        # View frontend logs
```

When running with Docker:
- Frontend: http://localhost (port 80)
- Backend API: http://localhost:8000
- Data persisted in `backend/data/` and `backend/models/`

## Architecture

### ML Architecture (Modal.com)

ML training and prediction runs on Modal.com, not locally:

```
┌─────────────────┐      ┌─────────────────────────────┐
│  FastAPI        │      │  Modal.com                  │
│  (Local)        │◄────►│  Python 3.12 + AutoGluon    │
│  modal_app/     │      │                             │
│  client.py      │      │  modal_app/functions.py     │
└─────────────────┘      │  - train_model()            │
                         │  - predict()                │
                         │  - get_model_status()       │
                         │  - get_feature_importance() │
                         │                             │
                         │  Modal Volume               │
                         │  └── boonta-models/         │
                         └─────────────────────────────┘
```

### Backend Structure (`backend/app/`)

Layered architecture with clear separation of concerns:

- **api/** - FastAPI route handlers (races, horses, entries, predictions, fetch, model, jockeys)
- **services/** - Business logic layer (race_service, prediction_service, feature_service)
- **repositories/** - Data access layer with base repository pattern
- **models/** - SQLAlchemy ORM models (race, horse, jockey, entry, result, prediction)
- **schemas/** - Pydantic validation schemas
- **ml/** - Local ML utilities (pace.py for pace prediction rules)
- **fetchers/** - External data scrapers (netkeiba.py with base class)

### Modal App Structure (`backend/modal_app/`)

Self-contained Modal functions (no external imports from app/):

- **functions.py** - All Modal functions with inline feature engineering
  - `train_model()` - Train AutoGluon model (timeout: 3600s, memory: 8GB)
  - `predict()` - Make predictions (timeout: 60s, memory: 4GB)
  - `get_model_status()` - Check model on Volume
  - `get_feature_importance()` - Get feature importance
  - `test_status()` - Local entrypoint for testing
  - `test_train()` - Local entrypoint for test training
- **client.py** - ModalClient class for calling Modal functions from FastAPI

### Frontend Structure (`frontend/src/`)

- **pages/** - Route components (Dashboard, RaceList, RaceDetail, DataInput, ModelStatus)
- **components/** - Reusable UI components organized by domain (common, race, prediction, charts)
- **hooks/** - React Query hooks for API data fetching
- **api/** - Axios client and API functions
- **types/** - TypeScript interfaces

### API Endpoints

All APIs are prefixed with `/api`:
- `/races` - Race CRUD
- `/horses` - Horse information
- `/jockeys` - Jockey statistics
- `/entries` - Race entries (出走馬)
- `/predictions` - ML predictions (uses Modal)
- `/fetch` - External data scraping triggers
- `/model` - ML model training and status (uses Modal)
  - `GET /model/status` - Check if model is trained
  - `POST /model/train` - Start training (async)
  - `GET /model/training-status/{call_id}` - Check training progress
  - `GET /model/feature-importance` - Get feature importance

### Database

SQLite with SQLAlchemy async support. Data stored in `backend/data/boonta.db`. ML models are stored on Modal Volume (not locally).

### Key Concepts

- **Running Styles (脚質)**: ESCAPE(逃げ), FRONT(先行), STALKER(差し), CLOSER(追込), VERSATILE(自在)
- **Pace Prediction**: Rule-based logic determining race pace (high/middle/slow) based on running style distribution
- **Bet Recommendations**: Focus on trifecta/trio/exacta with dark horse detection for value betting
- **Modal Volume**: Persistent storage for trained ML models on Modal.com

## Testing

### Running Tests

```bash
cd backend
pytest                              # Run all tests
pytest tests/unit/ -v               # Unit tests only
pytest -k "test_pace" -v            # Run specific test pattern
pytest --cov=app --cov-report=html  # With coverage report
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures (db_session, test_race, etc.)
├── fixtures/
│   └── factories.py         # Test data factories
├── unit/
│   ├── ml/
│   │   └── test_pace.py     # Pace prediction tests (~45 tests)
│   ├── services/
│   │   ├── test_prediction_service.py  # Prediction logic (~39 tests)
│   │   └── test_feature_service.py     # Feature engineering (~14 tests)
│   └── repositories/
│       ├── test_base_repository.py     # CRUD operations (~10 tests)
│       └── test_race_repository.py     # Race queries (~10 tests)
└── integration/
    └── api/                 # API endpoint tests (future)
```

### Key Test Patterns

- Use `pytest-asyncio` for async tests (asyncio_mode = "auto")
- In-memory SQLite (`sqlite+aiosqlite:///:memory:`)
- Modal client is mocked in tests (returns None for predictions)
- Transaction rollback after each test

### CI/CD

GitHub Actions workflows (triggered on push/PR to main):

**lint.yml**
- Lint (ruff) - strict, blocks merge
- Type check (mypy) - runs but doesn't block (continue-on-error)

**test.yml**
- pytest with coverage
- Python 3.10, 3.11 matrix
- Modal/AutoGluon excluded (mocked in tests)

## Code Patterns

### Repository Pattern

Repositories extend `BaseRepository[ModelType]`:
- `get(id)`, `get_all(skip, limit, filters)`, `count()`
- `create(data)`, `update(id, data)`, `delete(id)`
- Custom queries in subclasses (e.g., `get_with_entries()`)

### Service Pattern

Services encapsulate business logic:
- Accept `AsyncSession` in constructor
- Instantiate repositories internally
- Return Pydantic schemas or domain objects

### Modal Integration

- `get_modal_client()` returns singleton ModalClient
- ModalClient uses `modal.Function.from_name()` to get remote functions
- Prediction service calls Modal for ML predictions asynchronously
- Training is spawned async with `train_fn.spawn()` returning a call_id

### Feature Engineering

Feature engineering code exists in two places (must stay in sync):
- `backend/app/ml/features.py` - For local utilities (not used for ML anymore)
- `backend/modal_app/functions.py` - Inlined in Modal functions (used for training/prediction)

When updating features, update both locations.

## Training Data

### Location

Training data is stored at `backend/data/training/g1_races.csv`

### Required Columns

| Category | Columns |
|----------|---------|
| Basic | `horse_number`, `post_position`, `odds`, `popularity`, `weight` |
| Horse | `horse_age`, `horse_sex`, `horse_weight`, `horse_weight_diff` |
| Race | `distance`, `course_type`, `venue`, `track_condition`, `weather` |
| Style | `running_style` |
| Stats | `win_rate`, `place_rate`, `avg_position_last5`, `avg_last_3f`, `best_last_3f` |
| Jockey | `jockey_win_rate`, `jockey_venue_win_rate` |
| Target | `is_place` (1=placed, 0=not placed) |

### Collecting Training Data

```bash
cd backend
python scripts/collect_training_data.py --grade G1 --with-history
```

### Training Model

```bash
# Via Modal CLI (recommended, shows real-time logs)
modal run modal_app/functions.py::test_train

# Via API
curl -X POST http://localhost:8000/api/model/train
```
