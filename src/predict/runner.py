"""Prediction orchestrator: parse → features → predict → format."""
from __future__ import annotations

from pathlib import Path

from src.features.engineering import build_prediction_features
from src.model.client import ModalClient
from src.parser import KYI_FIELDS, KYI_RECORD_LENGTH
from src.parser.engine import parse_file
from src.predict.tenkai import format_tenkai


def run_prediction(
    kyi_path: Path,
    client: ModalClient | None = None,
    race_number: int | None = None,
) -> str:
    """Run full prediction pipeline for a KYI file.

    Args:
        kyi_path: Path to raw KYI file.
        client: ModalClient instance. If None, predictions are skipped.
        race_number: Optional specific race number to predict.

    Returns:
        Formatted 展開予想 text output.
    """
    # 1. Parse KYI
    kyi_df = parse_file(kyi_path, KYI_FIELDS, KYI_RECORD_LENGTH)

    # 2. Filter by race number if specified
    if race_number is not None:
        kyi_df = kyi_df[kyi_df["R"] == race_number]
        if len(kyi_df) == 0:
            return f"Race {race_number} not found in {kyi_path.name}"

    # 3. Build prediction features
    features_df = build_prediction_features(kyi_df)

    # 4. Group by race_key and predict
    outputs: list[str] = []

    for race_key, race_df in features_df.groupby("race_key"):
        race_df = race_df.reset_index(drop=True)

        # Get ML predictions if client available
        predictions = None
        if client is not None:
            feature_cols = [c for c in race_df.columns
                           if c not in ("race_key", "horse_number", "horse_name")]
            features_list = race_df[feature_cols].to_dict("records")

            try:
                result = client.predict(features_list)
                if result.get("success"):
                    predictions = result["predictions"]
            except Exception as e:
                print(f"Prediction failed for {race_key}: {e}")

        output = format_tenkai(race_df, predictions)
        outputs.append(output)

    return "\n\n".join(outputs) if outputs else "No races found."
