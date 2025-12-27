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
