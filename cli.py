"""Boonta v2 CLI entry point."""
from __future__ import annotations

from pathlib import Path

import click
import pandas as pd

from config.settings import Settings


@click.group()
def cli():
    """Boonta - JRDB horse racing prediction system."""
    pass


@cli.command()
@click.option("--type", "file_type", required=True, type=click.Choice(["KYI", "SED", "HJC"]))
@click.option("--date", "date_str", help="Date in YYMMDD format (e.g. 260405)")
@click.option("--date-range", "date_range", nargs=2, help="Start and end dates (YYYYMMDD)")
def download(file_type: str, date_str: str | None, date_range: tuple[str, str] | None):
    """Download JRDB files."""
    from src.download.jrdb import JRDBDownloader

    settings = Settings()
    downloader = JRDBDownloader(settings)

    if date_str:
        click.echo(f"Downloading {file_type} for {date_str}...")
        extracted = downloader.download_file(file_type, date_str)
        for p in extracted:
            click.echo(f"  Extracted: {p}")
    elif date_range:
        click.echo(f"Downloading {file_type} for date range {date_range[0]} to {date_range[1]}...")
        dates = _generate_dates(date_range[0], date_range[1])
        results = downloader.download_date_range(file_type, dates)
        for d, paths in results.items():
            click.echo(f"  {d}: {len(paths)} files")
    else:
        click.echo("Please specify --date or --date-range")


@cli.command()
@click.option("--type", "file_type", type=click.Choice(["KYI", "SED", "HJC"]))
@click.option("--date", "date_str", help="Date in YYMMDD format")
@click.option("--all", "parse_all", is_flag=True, help="Parse all files in data/raw/")
def parse(file_type: str | None, date_str: str | None, parse_all: bool):
    """Parse raw JRDB files to CSV."""
    from src.parser import (
        HJC_FIELDS, HJC_RECORD_LENGTH,
        KYI_FIELDS, KYI_RECORD_LENGTH,
        SED_FIELDS, SED_RECORD_LENGTH,
    )
    from src.parser.engine import parse_file

    settings = Settings()
    settings.data_processed_dir.mkdir(parents=True, exist_ok=True)

    type_config = {
        "KYI": (KYI_FIELDS, KYI_RECORD_LENGTH, "KYI"),
        "SED": (SED_FIELDS, SED_RECORD_LENGTH, "SED"),
        "HJC": (HJC_FIELDS, HJC_RECORD_LENGTH, "HJC"),
    }

    if parse_all:
        for ft, (fields, rec_len, prefix) in type_config.items():
            _parse_files(settings, fields, rec_len, prefix, ft)
    elif file_type and date_str:
        fields, rec_len, prefix = type_config[file_type]
        path = settings.data_raw_dir / f"{prefix}{date_str}.txt"
        if not path.exists():
            click.echo(f"File not found: {path}")
            return
        df = parse_file(path, fields, rec_len)
        out = settings.data_processed_dir / f"{prefix.lower()}_{date_str}.csv"
        df.to_csv(out, index=False)
        click.echo(f"Parsed {len(df)} records → {out}")
    else:
        click.echo("Please specify --type and --date, or --all")


@cli.command()
@click.option("--date-range", nargs=2, required=True, help="Start and end dates (YYYYMMDD)")
@click.option("--time-limit", default=1800, help="Training time limit in seconds")
def train(date_range: tuple[str, str], time_limit: int):
    """Train ML model from KYI + SED data."""
    from src.features.engineering import build_training_features
    from src.model.client import ModalClient
    from src.parser import KYI_FIELDS, KYI_RECORD_LENGTH, SED_FIELDS, SED_RECORD_LENGTH
    from src.parser.engine import parse_file

    settings = Settings()

    click.echo(f"Building training features from {date_range[0]} to {date_range[1]}...")

    # Parse all KYI and SED files in the date range
    kyi_frames, sed_frames = [], []
    for path in sorted(settings.data_raw_dir.glob("KYI*.txt")):
        kyi_frames.append(parse_file(path, KYI_FIELDS, KYI_RECORD_LENGTH))
    for path in sorted(settings.data_raw_dir.glob("SED*.txt")):
        sed_frames.append(parse_file(path, SED_FIELDS, SED_RECORD_LENGTH))

    if not kyi_frames or not sed_frames:
        click.echo("No KYI/SED files found in data/raw/")
        return

    kyi_df = pd.concat(kyi_frames, ignore_index=True)
    sed_df = pd.concat(sed_frames, ignore_index=True)

    training_df = build_training_features(kyi_df, sed_df)
    click.echo(f"Training data: {len(training_df)} samples, {len(training_df.columns)} features")

    csv_data = training_df.to_csv(index=False)

    click.echo(f"Sending to Modal for training (time_limit={time_limit}s)...")
    client = ModalClient()
    result = client.train(csv_data, time_limit=time_limit)

    if result.get("success"):
        click.echo(f"Training complete! Best score: {result.get('best_score')}")
        click.echo(f"Best model: {result.get('best_model')}")
    else:
        click.echo(f"Training failed: {result.get('error')}")


@cli.command()
@click.option("--date", "date_str", required=True, help="Date in YYMMDD format")
@click.option("--race", "race_number", type=int, help="Specific race number")
@click.option("--no-ml", is_flag=True, help="Skip ML predictions (show forecast only)")
def predict(date_str: str, race_number: int | None, no_ml: bool):
    """Run predictions and show 展開予想."""
    from src.model.client import ModalClient
    from src.predict.runner import run_prediction

    settings = Settings()
    kyi_path = settings.data_raw_dir / f"KYI{date_str}.txt"

    if not kyi_path.exists():
        click.echo(f"KYI file not found: {kyi_path}")
        return

    client = None if no_ml else ModalClient()

    output = run_prediction(kyi_path, client=client, race_number=race_number)
    click.echo(output)


@cli.command()
@click.option("--date-range", nargs=2, required=True, help="Start and end dates (YYYYMMDD)")
@click.option("--strategy", default="fukusho_top3",
              type=click.Choice(["fukusho_top3", "umaren_top2", "sanrenpuku_top3"]))
def evaluate(date_range: tuple[str, str], strategy: str):
    """Evaluate ROI using predictions and HJC payoff data."""
    from src.features.engineering import build_prediction_features
    from src.model.client import ModalClient
    from src.parser import (
        HJC_FIELDS, HJC_RECORD_LENGTH,
        KYI_FIELDS, KYI_RECORD_LENGTH,
    )
    from src.parser.engine import build_race_key, parse_file
    from src.predict.roi import evaluate_roi

    settings = Settings()

    click.echo(f"Evaluating ROI ({strategy}) for {date_range[0]} to {date_range[1]}...")

    # Parse KYI files
    kyi_frames = []
    for path in sorted(settings.data_raw_dir.glob("KYI*.txt")):
        kyi_frames.append(parse_file(path, KYI_FIELDS, KYI_RECORD_LENGTH))

    if not kyi_frames:
        click.echo("No KYI files found")
        return

    kyi_df = pd.concat(kyi_frames, ignore_index=True)
    features_df = build_prediction_features(kyi_df)

    # Get predictions from Modal
    click.echo("Getting predictions from Modal...")
    client = ModalClient()
    all_predictions = []

    for race_key, race_df in features_df.groupby("race_key"):
        feature_cols = [c for c in race_df.columns
                       if c not in ("race_key", "horse_number", "horse_name")]
        features_list = race_df[feature_cols].to_dict("records")

        try:
            result = client.predict(features_list)
            if result.get("success"):
                race_df = race_df.copy()
                race_df["predict_prob"] = result["predictions"]
                all_predictions.append(race_df[["race_key", "horse_number", "predict_prob"]])
        except Exception as e:
            click.echo(f"  Prediction failed for {race_key}: {e}")

    if not all_predictions:
        click.echo("No predictions generated")
        return

    predictions_df = pd.concat(all_predictions, ignore_index=True)

    # Parse HJC files
    hjc_frames = []
    for path in sorted(settings.data_raw_dir.glob("HJC*.txt")):
        df = parse_file(path, HJC_FIELDS, HJC_RECORD_LENGTH)
        df["race_key"] = df.apply(lambda row: build_race_key(row.to_dict()), axis=1)
        hjc_frames.append(df)

    if not hjc_frames:
        click.echo("No HJC files found")
        return

    hjc_df = pd.concat(hjc_frames, ignore_index=True)

    # Evaluate ROI
    result = evaluate_roi(predictions_df, hjc_df, strategy)

    click.echo(f"\n{'=' * 40}")
    click.echo(f"戦略: {result['strategy']}")
    click.echo(f"レース数: {result['race_count']}")
    click.echo(f"投資額: {result['total_bets']:,}円")
    click.echo(f"回収額: {result['total_return']:,}円")
    click.echo(f"回収率: {result['roi']}%")
    click.echo(f"的中数: {result['hit_count']}")
    click.echo(f"{'=' * 40}")


def _generate_dates(start: str, end: str) -> list[str]:
    """Generate YYMMDD date strings from YYYYMMDD range."""
    from datetime import datetime, timedelta

    start_dt = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")

    dates = []
    current = start_dt
    while current <= end_dt:
        dates.append(current.strftime("%y%m%d"))
        current += timedelta(days=1)
    return dates


def _parse_files(settings: Settings, fields: list, rec_len: int, prefix: str, ft: str):
    """Parse all files of a given type in data/raw/."""
    from src.parser.engine import parse_file

    paths = sorted(settings.data_raw_dir.glob(f"{prefix}*.txt"))
    if not paths:
        click.echo(f"No {ft} files found")
        return

    all_frames = []
    for path in paths:
        df = parse_file(path, fields, rec_len)
        all_frames.append(df)
        click.echo(f"  Parsed {path.name}: {len(df)} records")

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        out = settings.data_processed_dir / f"{prefix.lower()}.csv"
        combined.to_csv(out, index=False)
        click.echo(f"  Combined → {out} ({len(combined)} total records)")


if __name__ == "__main__":
    cli()
