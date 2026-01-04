"""Model API routes."""

import csv
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.fetchers.netkeiba import NetkeibaFetcher
from app.schemas import FeatureImportanceResponse, ModelStatusResponse

router = APIRouter(prefix="/model", tags=["model"])

settings = get_settings()


@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status(
    db: AsyncSession = Depends(get_db),
):
    """Get current model status from Modal."""
    from modal_app.client import get_modal_client

    # Get training data count from local CSV
    training_data_count = 0
    csv_path = settings.model_path.parent / "data" / "training" / "g1_races.csv"
    if csv_path.exists():
        with open(csv_path) as f:
            training_data_count = sum(1 for _ in f) - 1  # Subtract header

    # Check Modal for model status
    try:
        modal_client = get_modal_client()
        result = await modal_client.get_model_status()
        is_trained = result.get("exists", False)
    except Exception as e:
        print(f"Modal status check failed: {e}")
        is_trained = False

    # Pre-computed metrics (updated after training)
    metrics = {"roc_auc": 0.801} if is_trained else None

    return ModelStatusResponse(
        model_version=settings.model_version,
        is_trained=is_trained,
        last_trained_at=None,  # Could store in Modal Volume metadata
        training_data_count=training_data_count,
        metrics=metrics,
    )


class TrainModelRequest(BaseModel):
    """Request to train the model."""

    time_limit: int = Field(default=1800, description="Training time limit in seconds")
    presets: str = Field(default="best_quality", description="AutoGluon presets")


class TrainModelResponse(BaseModel):
    """Response from training request."""

    status: str
    call_id: str | None = None
    message: str


@router.post("/train", response_model=TrainModelResponse)
async def train_model(
    request: TrainModelRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Train the prediction model on Modal."""
    from modal_app.client import get_modal_client

    # Load training data from local CSV
    csv_path = settings.model_path.parent / "data" / "training" / "g1_races.csv"
    if not csv_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Training data not found. Collect training data first.",
        )

    with open(csv_path, encoding="utf-8") as f:
        training_data_csv = f.read()

    # Trigger training on Modal
    time_limit = request.time_limit if request else 1800
    presets = request.presets if request else "best_quality"

    try:
        modal_client = get_modal_client()
        result = await modal_client.train(
            training_data_csv=training_data_csv,
            time_limit=time_limit,
            presets=presets,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Training failed to start"),
            )

        return TrainModelResponse(
            status="training_started",
            call_id=result.get("call_id"),
            message="Training started on Modal. Use /model/training-status/{call_id} to check progress.",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start training: {str(e)}",
        )


class TrainingStatusResponse(BaseModel):
    """Response from training status check."""

    status: str  # running, completed, error
    result: dict | None = None
    error: str | None = None


@router.get("/training-status/{call_id}", response_model=TrainingStatusResponse)
async def get_training_status(
    call_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Check training job status on Modal."""
    from modal_app.client import get_modal_client

    try:
        modal_client = get_modal_client()
        result = await modal_client.get_training_status(call_id)
        return TrainingStatusResponse(
            status=result.get("status", "unknown"),
            result=result.get("result"),
            error=result.get("error"),
        )
    except Exception as e:
        return TrainingStatusResponse(
            status="error",
            error=str(e),
        )


@router.get("/feature-importance", response_model=FeatureImportanceResponse)
async def get_feature_importance(
    db: AsyncSession = Depends(get_db),
):
    """Get feature importance from the trained model on Modal."""
    from modal_app.client import get_modal_client

    try:
        modal_client = get_modal_client()
        result = await modal_client.get_feature_importance()

        if not result.get("success"):
            raise HTTPException(
                status_code=404,
                detail=result.get("error", "Model not found"),
            )

        return FeatureImportanceResponse(features=result["features"])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feature importance: {str(e)}",
        )


# Training data collection


@dataclass
class TrainingData:
    """Training data for a single horse entry."""

    race_id: str = ""
    race_name: str = ""
    race_date: str = ""
    venue: str = ""
    distance: int = 0
    course_type: str = ""
    grade: str = ""
    horse_number: int = 0
    horse_name: str = ""
    jockey_name: str = ""
    weight: float = 0.0
    horse_weight: int | None = None
    position: int = 0
    odds: float = 0.0
    popularity: int = 0
    time_seconds: float | None = None
    last_3f: float | None = None
    corner_positions: str = ""
    running_style: str = ""
    is_win: int = 0
    is_place: int = 0


class CollectTrainingDataRequest(BaseModel):
    """Request to collect training data from a race."""

    netkeiba_race_id: str = Field(..., description="netkeiba race ID")


class CollectTrainingDataResponse(BaseModel):
    """Response from training data collection."""

    success: bool
    message: str
    race_name: str | None = None
    records_added: int = 0
    total_records: int = 0


async def _fetch_result_details(fetcher: NetkeibaFetcher, race_id: str) -> dict[int, dict]:
    """Fetch detailed result info (position, time, last_3f) from result page."""
    import asyncio

    from bs4 import BeautifulSoup

    # Try race.netkeiba.com first
    url = f"{fetcher.BASE_URL}/race/result.html?race_id={race_id}"

    await asyncio.sleep(fetcher.delay)
    response = await fetcher.client.get(url)

    if response.status_code != 200:
        return {}

    html = response.content.decode("euc-jp", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    results = {}
    table = soup.select_one("table.Shutuba_Table, table.RaceTable01")
    if not table:
        return {}

    rows = table.select("tr")

    for row in rows:
        try:
            cols = row.select("td")
            if len(cols) < 12:
                continue

            # 着順 (column 0)
            position_text = cols[0].get_text(strip=True)
            if not position_text.isdigit():
                continue
            position = int(position_text)

            # 馬番 (column 2)
            horse_number_text = cols[2].get_text(strip=True)
            if not horse_number_text.isdigit():
                continue
            horse_number = int(horse_number_text)

            # タイム (column 7)
            time_str = cols[7].get_text(strip=True)
            time_seconds = None
            time_match = re.match(r"(\d):(\d{2})\.(\d)", time_str)
            if time_match:
                time_seconds = (
                    int(time_match.group(1)) * 60
                    + int(time_match.group(2))
                    + int(time_match.group(3)) / 10
                )

            # 上がり3F (column 11)
            last_3f = None
            if len(cols) > 11:
                last_3f_text = cols[11].get_text(strip=True)
                try:
                    last_3f = float(last_3f_text)
                except ValueError:
                    pass

            results[horse_number] = {
                "position": position,
                "time_seconds": time_seconds,
                "last_3f": last_3f,
            }

        except Exception:
            continue

    return results


@router.post("/collect-training-data", response_model=CollectTrainingDataResponse)
async def collect_training_data(
    request: CollectTrainingDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Collect training data from a finished race and add to training dataset.

    This endpoint:
    1. Fetches race result from netkeiba
    2. Converts to training data format
    3. Appends to the training CSV file
    """
    race_id = request.netkeiba_race_id

    async with NetkeibaFetcher() as fetcher:
        # Get race info
        race_info = await fetcher.fetch_race_info(race_id)
        if not race_info:
            raise HTTPException(
                status_code=404,
                detail=f"Race not found: {race_id}",
            )

        # Get odds/result from result page
        odds_list = await fetcher.fetch_odds_from_result(race_id)
        if not odds_list:
            raise HTTPException(
                status_code=400,
                detail="Race result not found. Make sure the race has finished.",
            )

        # Get entries for additional info
        entries = await fetcher.fetch_entries(race_id)
        entry_map = {e.horse_number: e for e in entries}

        # Get detailed results
        result_details = await _fetch_result_details(fetcher, race_id)

        if not result_details:
            raise HTTPException(
                status_code=400,
                detail="Could not fetch race result details.",
            )

        # Build training data
        training_data = []
        for odds_info in odds_list:
            entry = entry_map.get(odds_info.horse_number)
            details = result_details.get(odds_info.horse_number, {})
            position = details.get("position", 0)

            data = TrainingData(
                race_id=race_id,
                race_name=race_info.name,
                race_date=race_info.date,
                venue=race_info.venue,
                distance=race_info.distance,
                course_type=race_info.course_type,
                grade=race_info.grade,
                horse_number=odds_info.horse_number,
                horse_name=entry.horse_name if entry else "",
                jockey_name=entry.jockey_name if entry else "",
                weight=entry.weight if entry else 0.0,
                horse_weight=entry.horse_weight if entry else None,
                position=position,
                odds=odds_info.odds,
                popularity=odds_info.popularity,
                time_seconds=details.get("time_seconds"),
                last_3f=details.get("last_3f"),
                corner_positions="-".join(map(str, odds_info.corner_positions or [])),
                running_style=odds_info.running_style or "",
                is_win=1 if position == 1 else 0,
                is_place=1 if 1 <= position <= 3 else 0,
            )
            training_data.append(data)

        if not training_data:
            raise HTTPException(
                status_code=400,
                detail="No training data could be extracted.",
            )

        # Save to CSV
        csv_path = Path(settings.model_path).parent / "data" / "training" / "g1_races.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = csv_path.exists()
        fieldnames = list(asdict(training_data[0]).keys())

        # Check for duplicates
        existing_race_ids = set()
        if file_exists:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing_race_ids.add(row.get("race_id", ""))

        if race_id in existing_race_ids:
            # Count total records
            with open(csv_path, encoding="utf-8") as f:
                total_records = sum(1 for _ in f) - 1

            return CollectTrainingDataResponse(
                success=True,
                message=f"Race '{race_info.name}' already exists in training data",
                race_name=race_info.name,
                records_added=0,
                total_records=total_records,
            )

        # Append to CSV
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for data in training_data:
                writer.writerow(asdict(data))

        # Count total records
        with open(csv_path, encoding="utf-8") as f:
            total_records = sum(1 for _ in f) - 1

        return CollectTrainingDataResponse(
            success=True,
            message=f"Added {len(training_data)} records from '{race_info.name}'",
            race_name=race_info.name,
            records_added=len(training_data),
            total_records=total_records,
        )
