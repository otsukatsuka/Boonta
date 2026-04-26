"""Boonta v2 CLI entry point."""
from __future__ import annotations

import click
import pandas as pd

from config.settings import Settings


@click.group()
def cli():
    """Boonta - JRDB horse racing prediction system."""
    pass


@cli.command()
@click.option("--port", default=8000, help="API port")
@click.option("--host", default="127.0.0.1", help="API host")
@click.option("--no-vite", is_flag=True, help="Skip starting the vite dev server")
@click.option("--reload/--no-reload", default=True, help="uvicorn --reload")
def serve(port: int, host: str, no_vite: bool, reload: bool):
    """Start API server (and the vite dev server unless --no-vite)."""
    import shutil
    import subprocess
    import signal
    import sys

    settings = Settings()
    web_dir = settings.project_root / "web"

    procs: list[subprocess.Popen] = []

    api_cmd = [
        "uvicorn", "src.api.main:app",
        "--host", host, "--port", str(port),
    ]
    if reload:
        api_cmd.append("--reload")
    click.echo(f"→ uvicorn http://{host}:{port}")
    procs.append(subprocess.Popen(api_cmd, cwd=settings.project_root))

    if not no_vite:
        if not web_dir.exists():
            click.echo(f"web/ not found at {web_dir}; run pnpm install there", err=True)
        else:
            pnpm = shutil.which("pnpm")
            if pnpm is None:
                click.echo("pnpm not found in PATH; skipping vite", err=True)
            else:
                click.echo("→ vite http://localhost:5173")
                procs.append(subprocess.Popen([pnpm, "dev"], cwd=web_dir))

    def _shutdown(*_):
        click.echo("\nshutting down...")
        for p in procs:
            try:
                p.send_signal(signal.SIGINT)
            except Exception:
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except Exception:
                p.kill()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # wait
    for p in procs:
        p.wait()


@cli.group()
def db():
    """Database management (init / ingest)."""
    pass


@cli.group()
def backtest():
    """Backtest strategies against stored predictions + payouts."""
    pass


@backtest.command("run")
@click.option("--strategy", default="all",
              help="Strategy id (or 'all' for all 6)")
@click.option("--date-range", "date_range", nargs=2, required=True,
              help="YYYYMMDD YYYYMMDD")
@click.option("--ev-threshold", type=float, default=1.0,
              help="EV threshold for ev_* strategies (ignored otherwise)")
@click.option("--no-sensitivity", is_flag=True,
              help="Skip ev_threshold sensitivity sweep")
def backtest_run(
    strategy: str,
    date_range: tuple[str, str],
    ev_threshold: float,
    no_sensitivity: bool,
):
    """Run backtest(s) and persist results to DB."""
    from datetime import datetime as _dt
    from src.backtest import (
        STRATEGIES,
        load_hjc_df,
        load_predictions_df,
        latest_model_version,
        run_backtest,
        run_sensitivity_sweep,
    )
    from src.backtest.runner import EV_STRATEGIES
    from src.db.session import session_scope

    date_from = _dt.strptime(date_range[0], "%Y%m%d").date()
    date_to = _dt.strptime(date_range[1], "%Y%m%d").date()
    targets = STRATEGIES if strategy == "all" else [strategy]
    for s in targets:
        if s not in STRATEGIES:
            click.echo(f"Unknown strategy: {s}", err=True)
            raise click.exceptions.Exit(1)

    with session_scope() as session:
        mv = latest_model_version(session)
        if mv is None:
            click.echo("No predictions in DB. Run predict first.", err=True)
            raise click.exceptions.Exit(1)
        click.echo(f"model_version={mv}, range={date_from}..{date_to}")

        preds_df = load_predictions_df(session, date_from, date_to, mv)
        hjc_df = load_hjc_df(session, date_from, date_to)
        if preds_df.empty or hjc_df.empty:
            click.echo("No predictions or payouts in date range", err=True)
            raise click.exceptions.Exit(1)

        for s in targets:
            try:
                run = run_backtest(
                    session,
                    strategy=s,
                    date_from=date_from,
                    date_to=date_to,
                    ev_threshold=ev_threshold,
                    model_version=mv,
                )
                click.echo(
                    f"  {s:<24} ROI={run.roi:>6.1f}%  "
                    f"hits={run.hits:>5}  bets={run.invested:>10,}  ret={run.returned:>10,}"
                )
                if not no_sensitivity and s in EV_STRATEGIES:
                    n = run_sensitivity_sweep(
                        session, run=run, preds_df=preds_df, hjc_df=hjc_df,
                    )
                    click.echo(f"    sensitivity sweep: {n} thresholds")
            except Exception as e:
                click.echo(f"  {s} failed: {e}", err=True)


@db.command("init")
def db_init():
    """Apply Alembic migrations and ensure WAL mode."""
    import subprocess
    import sys

    settings = Settings()
    alembic_ini = settings.project_root / "alembic.ini"
    # Use the same Python that's running cli.py — avoids PATH issues when the
    # user hasn't activated the venv but invokes via .venv/bin/python.
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
        cwd=settings.project_root,
        capture_output=True,
        text=True,
    )
    click.echo(result.stdout)
    if result.returncode != 0:
        click.echo(result.stderr, err=True)
        raise click.exceptions.Exit(1)

    from src.db.session import db_path
    click.echo(f"DB ready: {db_path(settings)}")


_INGEST_TYPES = ["KYI", "SED", "HJC", "BAC", "OW", "OU", "OT", "CYB", "KKA"]


def _ingest_one(session, file_type: str, date_str: str, settings) -> tuple[int, int, "date | None"]:
    """Run one parser+ingester for ``file_type`` / ``date_str``.

    Returns ``(records, touched, held_on)``. Returns ``(0, 0, None)`` when the
    raw file is missing.
    """
    from src.db.ingest import (
        held_on_from_filename,
        ingest_bac,
        ingest_cyb,
        ingest_hjc,
        ingest_kka,
        ingest_kyi,
        ingest_race_odds,
        ingest_sed,
    )
    from src.parser import (
        BAC_FIELDS,
        BAC_RECORD_LENGTH,
        CYB_FIELDS,
        CYB_RECORD_LENGTH,
        HJC_FIELDS,
        HJC_RECORD_LENGTH,
        KKA_FIELDS,
        KKA_RECORD_LENGTH,
        KYI_FIELDS,
        KYI_RECORD_LENGTH,
        SED_FIELDS,
        SED_RECORD_LENGTH,
        parse_ot_file,
        parse_ou_file,
        parse_ow_file,
    )
    from src.parser.engine import parse_file

    path = settings.data_raw_dir / f"{file_type}{date_str}.txt"
    if not path.exists():
        return 0, 0, None
    held_on = held_on_from_filename(path)

    if file_type in ("KYI", "SED", "BAC", "HJC", "CYB", "KKA"):
        fields, rec_len, fn = {
            "KYI": (KYI_FIELDS, KYI_RECORD_LENGTH, ingest_kyi),
            "SED": (SED_FIELDS, SED_RECORD_LENGTH, ingest_sed),
            "BAC": (BAC_FIELDS, BAC_RECORD_LENGTH, ingest_bac),
            "HJC": (HJC_FIELDS, HJC_RECORD_LENGTH, ingest_hjc),
            "CYB": (CYB_FIELDS, CYB_RECORD_LENGTH, ingest_cyb),
            "KKA": (KKA_FIELDS, KKA_RECORD_LENGTH, ingest_kka),
        }[file_type]
        df = parse_file(path, fields, rec_len)
        touched = fn(session, df, held_on)
        return len(df), touched, held_on

    # Odds files — separate parsers, share ingest_race_odds with bet_type.
    odds_spec = {
        "OW": (parse_ow_file, "wide"),
        "OU": (parse_ou_file, "umatan"),
        "OT": (parse_ot_file, "sanrenpuku"),
    }
    parser_fn, bet_type = odds_spec[file_type]
    df = parser_fn(path)
    touched = ingest_race_odds(session, df, bet_type)
    return len(df), touched, held_on


@db.command("ingest")
@click.option("--type", "file_type", required=True, type=click.Choice(_INGEST_TYPES))
@click.option("--date", "date_str", required=True, help="Date in YYMMDD format")
def db_ingest(file_type: str, date_str: str):
    """Ingest a single day's parsed JRDB file into the DB."""
    from src.db.session import session_scope

    settings = Settings()
    with session_scope() as session:
        records, touched, held_on = _ingest_one(session, file_type, date_str, settings)
    if held_on is None:
        path = settings.data_raw_dir / f"{file_type}{date_str}.txt"
        click.echo(f"File not found: {path}", err=True)
        raise click.exceptions.Exit(1)
    click.echo(f"{file_type} {date_str} ({held_on}): {records} records → {touched} touched")


@db.command("ingest-all")
@click.option("--date", "date_str", required=True, help="Date in YYMMDD format")
def db_ingest_all(date_str: str):
    """Ingest BAC + KYI + SED + HJC + OW + OU + OT + CYB + KKA for a day (missing skipped)."""
    from src.db.session import session_scope

    settings = Settings()
    pipeline = ["BAC", "KYI", "SED", "HJC", "OW", "OU", "OT", "CYB", "KKA"]
    with session_scope() as session:
        for ft in pipeline:
            records, touched, held_on = _ingest_one(session, ft, date_str, settings)
            if held_on is None:
                click.echo(f"  skip {ft}: not found")
            else:
                click.echo(f"  {ft}: {records} rec → {touched} touched (held_on={held_on})")


@cli.command()
@click.option("--type", "file_type", required=True, type=click.Choice(["KYI", "SED", "HJC", "BAC", "OW", "OU", "OT", "CYB", "KKA"]))
@click.option("--date", "date_str", help="Date in YYMMDD format (e.g. 260405)")
@click.option(
    "--date-range", "date_range", nargs=2,
    help="Start and end dates in YYYYMMDD format (e.g. 20250101 20251231)",
)
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
@click.option("--type", "file_type", type=click.Choice(["KYI", "SED", "HJC", "BAC", "OW", "OU", "OT", "CYB", "KKA"]))
@click.option("--date", "date_str", help="Date in YYMMDD format")
@click.option("--all", "parse_all", is_flag=True, help="Parse all files in data/raw/")
def parse(file_type: str | None, date_str: str | None, parse_all: bool):
    """Parse raw JRDB files to CSV."""
    from src.parser import (
        BAC_FIELDS,
        BAC_RECORD_LENGTH,
        HJC_FIELDS,
        HJC_RECORD_LENGTH,
        KYI_FIELDS,
        KYI_RECORD_LENGTH,
        SED_FIELDS,
        SED_RECORD_LENGTH,
    )
    from src.parser.engine import parse_file

    settings = Settings()
    settings.data_processed_dir.mkdir(parents=True, exist_ok=True)

    type_config = {
        "KYI": (KYI_FIELDS, KYI_RECORD_LENGTH, "KYI"),
        "SED": (SED_FIELDS, SED_RECORD_LENGTH, "SED"),
        "HJC": (HJC_FIELDS, HJC_RECORD_LENGTH, "HJC"),
        "BAC": (BAC_FIELDS, BAC_RECORD_LENGTH, "BAC"),
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
@click.option("--time-limit", default=7200, help="AutoGluon training time limit in seconds")
@click.option(
    "--model-type",
    type=click.Choice(["autogluon", "lambdarank", "both"]),
    default="autogluon",
    help="autogluon = is_place binary, lambdarank = per-race ranker, both = train both",
)
@click.option("--lambdarank-rounds", default=3000, help="LightGBM num_boost_round")
def train(
    date_range: tuple[str, str],
    time_limit: int,
    model_type: str,
    lambdarank_rounds: int,
):
    """Train ML model from KYI + SED data."""
    from src.features.engineering import build_training_features
    from src.model.client import ModalClient
    from src.parser import KYI_FIELDS, KYI_RECORD_LENGTH, SED_FIELDS, SED_RECORD_LENGTH
    from src.parser.engine import parse_file

    settings = Settings()

    click.echo(f"Building training features from {date_range[0]} to {date_range[1]}...")

    # Parse KYI and SED files in the date range
    kyi_frames, sed_frames = [], []
    kyi_paths = _filter_by_date_range(
        sorted(settings.data_raw_dir.glob("KYI*.txt")), date_range,
    )
    sed_paths = _filter_by_date_range(
        sorted(settings.data_raw_dir.glob("SED*.txt")), date_range,
    )
    click.echo(f"Found {len(kyi_paths)} KYI and {len(sed_paths)} SED files in range")
    for path in kyi_paths:
        kyi_frames.append(parse_file(path, KYI_FIELDS, KYI_RECORD_LENGTH))
    for path in sed_paths:
        sed_frames.append(parse_file(path, SED_FIELDS, SED_RECORD_LENGTH))

    if not kyi_frames or not sed_frames:
        click.echo("No KYI/SED files found in data/raw/")
        return

    kyi_df = pd.concat(kyi_frames, ignore_index=True)
    sed_df = pd.concat(sed_frames, ignore_index=True)

    training_df = build_training_features(kyi_df, sed_df)
    click.echo(f"Training data: {len(training_df)} samples, {len(training_df.columns)} features")

    csv_data = training_df.to_csv(index=False)
    client = ModalClient()

    if model_type in {"autogluon", "both"}:
        click.echo(f"Training AutoGluon (time_limit={time_limit}s)...")
        result = client.train(csv_data, time_limit=time_limit)
        if result.get("success"):
            click.echo(
                f"AutoGluon done. Best AUC: {result.get('best_score')} "
                f"({result.get('best_model')}); Brier={result.get('brier')} "
                f"Hit@3={result.get('hit_at_3')} ECE={result.get('ece')}"
            )
            _record_training_run(result, time_limit=time_limit)
        else:
            click.echo(f"AutoGluon training failed: {result.get('error')}")
            if model_type == "autogluon":
                return

    if model_type in {"lambdarank", "both"}:
        click.echo(f"Training LightGBM lambdarank (num_boost_round={lambdarank_rounds})...")
        rank_result = client.train_lambdarank(
            csv_data,
            num_boost_round=lambdarank_rounds,
        )
        if rank_result.get("success"):
            click.echo(
                f"Lambdarank done. best_iter={rank_result.get('best_iteration')} "
                f"ndcg@3={rank_result.get('validation_ndcg_at_3')} "
                f"hit@1={rank_result.get('validation_hit_at_1')} "
                f"T={rank_result.get('optimal_temperature')} "
                f"NLL={rank_result.get('validation_nll')}"
            )
        else:
            click.echo(f"Lambdarank training failed: {rank_result.get('error')}")


def _record_training_run(result: dict, time_limit: int) -> None:
    """Insert a TrainingRun row, mark prior DEPLOYED rows as archived."""
    import json
    from datetime import datetime, timezone

    from sqlalchemy import select, update

    from src.db.models import TrainingRun
    from src.db.session import session_scope

    settings = Settings()
    leaderboard = result.get("leaderboard") or []
    eval_metric = result.get("eval_metric")
    best_score = result.get("best_score")

    auc_val = best_score if eval_metric == "roc_auc" else None
    logloss_val = best_score if eval_metric == "log_loss" else None

    trained_at_raw = result.get("trained_at")
    try:
        trained_at = (
            datetime.fromisoformat(str(trained_at_raw).replace("Z", "+00:00"))
            if trained_at_raw
            else datetime.now(timezone.utc)
        )
    except ValueError:
        trained_at = datetime.now(timezone.utc)

    base_run_id = f"v{trained_at.strftime('%y.%m.%d')}"
    with session_scope() as session:
        run_id = base_run_id
        suffix = 2
        while session.scalar(
            select(TrainingRun).where(TrainingRun.run_id == run_id)
        ):
            run_id = f"{base_run_id}-{suffix}"
            suffix += 1

        session.execute(
            update(TrainingRun)
            .where(TrainingRun.status == "DEPLOYED")
            .values(status="archived")
        )
        session.add(
            TrainingRun(
                run_id=run_id,
                trained_at=trained_at.replace(tzinfo=None),
                preset=result.get("presets_used") or settings.autogluon_presets,
                logloss=logloss_val,
                auc=auc_val,
                brier=result.get("brier"),
                hit_at_3=result.get("hit_at_3"),
                ece=result.get("ece"),
                train_time_seconds=result.get("train_time_seconds"),
                num_samples=result.get("num_samples"),
                status="DEPLOYED",
                leaderboard_json=json.dumps(leaderboard) if leaderboard else None,
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )
        )
    click.echo(f"Recorded training_run row {run_id} (DEPLOYED).")


@cli.command()
@click.option("--date", "date_str", required=True, help="Date in YYMMDD format")
@click.option("--race", "race_number", type=int, help="Specific race number")
@click.option("--no-ml", is_flag=True, help="Skip ML predictions (show forecast only)")
@click.option("--no-bet", is_flag=True, help="Skip EV ranking and bet recommendations")
@click.option("--ev-threshold", type=float, default=1.0,
              help="Minimum EV for tansho/fukusho picks (default 1.0 = break-even)")
def predict(
    date_str: str, race_number: int | None, no_ml: bool,
    no_bet: bool, ev_threshold: float,
):
    """Run predictions and show 展開予想."""
    from src.model.client import ModalClient
    from src.predict.runner import run_prediction

    settings = Settings()
    kyi_path = settings.data_raw_dir / f"KYI{date_str}.txt"

    if not kyi_path.exists():
        click.echo(f"KYI file not found: {kyi_path}")
        return

    client = None if no_ml else ModalClient()

    output = run_prediction(
        kyi_path,
        client=client,
        race_number=race_number,
        show_bets=not no_bet,
        ev_threshold=ev_threshold,
    )
    click.echo(output)


@cli.command()
@click.option("--date-range", nargs=2, required=True, help="Start and end dates (YYYYMMDD)")
@click.option("--strategy", default="fukusho_top3",
              type=click.Choice([
                  "fukusho_top3", "umaren_top2", "sanrenpuku_top3",
                  "ev_tansho", "ev_fukusho", "ev_sanrenpuku_nagashi",
              ]))
@click.option("--ev-threshold", type=float, default=1.0,
              help="Minimum EV for EV-based strategies (ignored otherwise)")
def evaluate(date_range: tuple[str, str], strategy: str, ev_threshold: float):
    """Evaluate ROI using predictions and HJC payoff data."""
    from src.features.engineering import build_prediction_features
    from src.model.client import ModalClient
    from src.parser import (
        HJC_FIELDS,
        HJC_RECORD_LENGTH,
        KYI_FIELDS,
        KYI_RECORD_LENGTH,
    )
    from src.parser.engine import build_race_key, parse_file
    from src.predict.roi import evaluate_roi

    settings = Settings()

    label = f"{strategy}, ev>{ev_threshold}" if strategy.startswith("ev_") else strategy
    click.echo(f"Evaluating ROI ({label}) for {date_range[0]} to {date_range[1]}...")

    # Parse KYI files in date range
    kyi_paths = _filter_by_date_range(
        sorted(settings.data_raw_dir.glob("KYI*.txt")), date_range,
    )
    kyi_frames = []
    for path in kyi_paths:
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
                       if c not in ("race_key", "horse_name", "fukusho_odds")]
        features_list = race_df[feature_cols].to_dict("records")

        try:
            result = client.predict(features_list)
            if result.get("success"):
                race_df = race_df.copy()
                race_df["predict_prob"] = result["predictions"]
                keep = ["race_key", "horse_number", "predict_prob", "odds"]
                if "fukusho_odds" in race_df.columns:
                    keep.append("fukusho_odds")
                all_predictions.append(race_df[keep])
        except Exception as e:
            click.echo(f"  Prediction failed for {race_key}: {e}")

    if not all_predictions:
        click.echo("No predictions generated")
        return

    predictions_df = pd.concat(all_predictions, ignore_index=True)

    # Parse HJC files in date range
    hjc_paths = _filter_by_date_range(
        sorted(settings.data_raw_dir.glob("HJC*.txt")), date_range,
    )
    hjc_frames = []
    for path in hjc_paths:
        df = parse_file(path, HJC_FIELDS, HJC_RECORD_LENGTH)
        df["race_key"] = df.apply(lambda row: build_race_key(row.to_dict()), axis=1)
        hjc_frames.append(df)

    if not hjc_frames:
        click.echo("No HJC files found")
        return

    hjc_df = pd.concat(hjc_frames, ignore_index=True)

    # Evaluate ROI
    result = evaluate_roi(predictions_df, hjc_df, strategy, ev_threshold=ev_threshold)

    click.echo(f"\n{'=' * 40}")
    click.echo(f"戦略: {result['strategy']}")
    click.echo(f"レース数: {result['race_count']}")
    if "bet_race_count" in result:
        click.echo(f"購入レース数: {result['bet_race_count']}")
    click.echo(f"投資額: {result['total_bets']:,}円")
    click.echo(f"回収額: {result['total_return']:,}円")
    click.echo(f"回収率: {result['roi']}%")
    click.echo(f"的中数: {result['hit_count']}")
    click.echo(f"{'=' * 40}")


def _filter_by_date_range(paths: list, date_range: tuple[str, str]) -> list:
    """Filter file paths by YYYYMMDD date range. Filenames use YYMMDD."""
    from datetime import datetime

    start = datetime.strptime(date_range[0], "%Y%m%d")
    end = datetime.strptime(date_range[1], "%Y%m%d")
    filtered = []
    for p in paths:
        date_part = p.stem[3:]  # "KYI200105" → "200105"
        if len(date_part) != 6 or not date_part.isdigit():
            continue
        try:
            file_date = datetime.strptime(date_part, "%y%m%d")
            if start <= file_date <= end:
                filtered.append(p)
        except ValueError:
            continue
    return filtered


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
        try:
            df = parse_file(path, fields, rec_len)
            all_frames.append(df)
            click.echo(f"  Parsed {path.name}: {len(df)} records")
        except Exception as e:
            click.echo(f"  Error parsing {path.name}: {e}", err=True)

    if all_frames:
        combined = pd.concat(all_frames, ignore_index=True)
        out = settings.data_processed_dir / f"{prefix.lower()}.csv"
        combined.to_csv(out, index=False)
        click.echo(f"  Combined → {out} ({len(combined)} total records)")


@cli.command()
@click.option("--race-key", "race_key", required=True, help="Race key (e.g. 0526010101)")
@click.option("--ev-threshold", type=float, default=1.10,
              help="Minimum EV for recommended picks (default 1.10)")
@click.option("--max-bets", type=int, default=10,
              help="Cap on bets shown per bet type")
def multibet(race_key: str, ev_threshold: float, max_bets: int):
    """Show multibet EV table + recommended picks for one race.

    Requires:
      * Race ingested (BAC/KYI) so HorseEntry rows exist
      * Pre-race odds ingested (OW/OU/OT) for combination EV
      * Predictions stored (prob from AutoGluon, prob_win from lambdarank)
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from src.db.models import HorseEntry, Prediction, Race, RaceOdds
    from src.db.session import session_scope
    from src.predict.multibet import (
        compute_fuku_ev,
        compute_sanrenpuku_ev,
        compute_tan_ev,
        compute_umatan_ev,
        compute_wide_ev,
        recommend_threshold,
    )

    with session_scope() as session:
        race = session.scalar(
            select(Race)
            .where(Race.race_key == race_key)
            .options(selectinload(Race.horses).selectinload(HorseEntry.predictions))
        )
        if race is None:
            click.echo(f"Race not found: {race_key}", err=True)
            raise click.exceptions.Exit(1)

        odds_row = session.scalar(
            select(RaceOdds).where(RaceOdds.race_id == race.id)
        )
        horses = sorted(race.horses, key=lambda h: h.horse_number)
        if not horses:
            click.echo(f"No horses for race {race_key}", err=True)
            raise click.exceptions.Exit(1)

        horse_numbers = [int(h.horse_number) for h in horses]
        odds_tan = {int(h.horse_number): float(h.odds) for h in horses if h.odds}
        odds_fuku = {int(h.horse_number): float(h.fukusho_odds) for h in horses if h.fukusho_odds}

        # Pull latest prediction per horse — prefer prob_win from lambdarank model
        prob_win: list[float] = []
        prob_top3: list[float] = []
        for h in horses:
            preds = sorted(h.predictions, key=lambda p: p.predicted_at, reverse=True)
            latest = preds[0] if preds else None
            if latest is None:
                prob_win.append(0.0)
                prob_top3.append(0.0)
                continue
            pw = latest.prob_win if latest.prob_win is not None else (latest.prob / 3.0)
            pt3 = latest.prob_top3 if latest.prob_top3 is not None else latest.prob
            prob_win.append(float(pw))
            prob_top3.append(float(pt3))

        click.echo(f"Race: {race_key} ({race.held_on}) — {len(horses)} horses")

        # Tan/fuku
        tan = compute_tan_ev(horse_numbers, prob_win, odds_tan)
        click.echo("\n[単勝 EV >= threshold]")
        for r in recommend_threshold(tan, ev_threshold, max_bets):
            click.echo(
                f"  ⛬ horse={r['horse']:2d} prob={r['prob']:.3f} "
                f"odds={r['odds']:.1f} ev={r['ev']:.3f}"
            )

        fuku = compute_fuku_ev(horse_numbers, prob_top3, odds_fuku)
        click.echo("\n[複勝 EV >= threshold]")
        for r in recommend_threshold(fuku, ev_threshold, max_bets):
            click.echo(
                f"  ⛬ horse={r['horse']:2d} prob={r['prob']:.3f} "
                f"odds={r['odds']:.1f} ev={r['ev']:.3f}"
            )

        # Combination odds — only if ingested
        if odds_row is None:
            click.echo("\n(No race_odds — ingest OW/OU/OT to see combination EVs)")
            return

        if odds_row.wide:
            wide = compute_wide_ev(horse_numbers, prob_win, odds_row.wide)
            click.echo("\n[ワイド EV >= threshold]")
            for r in recommend_threshold(wide, ev_threshold, max_bets):
                click.echo(
                    f"  ⛬ {r['key']} prob={r['prob']:.3f} "
                    f"odds={r['odds']:.1f} ev={r['ev']:.3f}"
                )

        if odds_row.umatan:
            um = compute_umatan_ev(horse_numbers, prob_win, odds_row.umatan)
            click.echo("\n[馬単 EV >= threshold]")
            for r in recommend_threshold(um, ev_threshold, max_bets):
                click.echo(
                    f"  ⛬ {r['key']} prob={r['prob']:.3f} "
                    f"odds={r['odds']:.1f} ev={r['ev']:.3f}"
                )

        if odds_row.sanrenpuku:
            sp = compute_sanrenpuku_ev(horse_numbers, prob_win, odds_row.sanrenpuku)
            click.echo("\n[三連複 EV >= threshold]")
            for r in recommend_threshold(sp, ev_threshold, max_bets):
                click.echo(
                    f"  ⛬ {r['key']} prob={r['prob']:.3f} "
                    f"odds={r['odds']:.1f} ev={r['ev']:.3f}"
                )


if __name__ == "__main__":
    cli()
