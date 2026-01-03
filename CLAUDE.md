# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Boonta is a horse racing prediction AI service for Japanese G1 races. It uses machine learning (AutoGluon) to predict race outcomes based on historical data, running styles, jockey statistics, and workout information.

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

### Backend Structure (`backend/app/`)

Layered architecture with clear separation of concerns:

- **api/** - FastAPI route handlers (races, horses, entries, predictions, fetch, model, jockeys)
- **services/** - Business logic layer (race_service, prediction_service, feature_service)
- **repositories/** - Data access layer with base repository pattern
- **models/** - SQLAlchemy ORM models (race, horse, jockey, entry, result, prediction)
- **schemas/** - Pydantic validation schemas
- **ml/** - Machine learning components (trainer, predictor, features, pace)
- **fetchers/** - External data scrapers (netkeiba.py with base class)

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
- `/predictions` - ML predictions
- `/fetch` - External data scraping triggers
- `/model` - ML model training and status

### Database

SQLite with SQLAlchemy async support. Data stored in `backend/data/boonta.db`. ML models saved in `backend/models/`.

### Key Concepts

- **Running Styles (脚質)**: ESCAPE(逃げ), FRONT(先行), STALKER(差し), CLOSER(追込), VERSATILE(自在)
- **Pace Prediction**: Rule-based logic determining race pace (high/middle/slow) based on running style distribution
- **Bet Recommendations**: Focus on trifecta/trio/exacta with dark horse detection for value betting

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
- Mock AutoGluon predictor in CI (returns None)
- Transaction rollback after each test

### CI/CD

GitHub Actions runs on push/PR to main:
- Lint (ruff) → Type check (mypy) → Tests (pytest)
- Python 3.10, 3.11 matrix
- AutoGluon excluded from CI dependencies (mocked in tests)

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

### ML Integration

- `get_ml_predictor()` lazy-loads AutoGluon model
- Returns `None` if model not trained
- Prediction service handles both ML and rule-based fallback
