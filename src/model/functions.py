"""Modal functions for AutoGluon training and prediction.

IMPORTANT: This module is self-contained. It MUST NOT import from src/.
All preprocessing logic is defined inline to match src/features/ logic.
Keep these in sync when updating features.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from io import StringIO

import modal
import numpy as np
import pandas as pd

# --- Modal App Setup ---
app = modal.App("boonta-ml")

autogluon_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgomp1")
    .pip_install(
        "autogluon.tabular[all]==1.4.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    )
)

model_volume = modal.Volume.from_name("boonta-models", create_if_missing=True)
VOLUME_PATH = "/models"

# --- Inline Preprocessing (mirrors src/features/) ---

CATEGORICAL_COLS = [
    "pace_forecast", "tenkai_symbol", "running_style",
    "distance_aptitude", "heavy_track_code",
    # === Phase 1-A 追加 ===
    "marker_overall", "marker_idm", "marker_info", "marker_jockey",
    "marker_stable", "marker_training", "marker_gekisou",
    "turf_aptitude", "dirt_aptitude",
    "blinker", "sex_code", "horse_mark_code", "apprentice", "transport",
    "demotion_flag", "gekisou_type", "rest_reason", "pasture_rank",
    "stable_eval_code", "training_arrow_code",
    "running_form", "body_shape",
    "body_summary_1", "body_summary_2", "body_summary_3",
    "horse_remark_1", "horse_remark_2", "horse_remark_3",
    "kyi_flags",
]

NUMERICAL_DEFAULTS = {
    # 既存
    "idm": 50.0,
    "jockey_index": 50.0,
    "info_index": 50.0,
    "overall_index": 50.0,
    "training_index": 50.0,
    "stable_index": 50.0,
    "ten_index": 50.0,
    "pace_index": 50.0,
    "agari_index": 50.0,
    "position_index": 50.0,
    "odds": 10.0,
    "popularity": 8,
    "horse_number": 5,
    "waku": 4,
    "weight_carried": 55.0,
    "mid_position": 8,
    "mid_gap": 5,
    "mid_position_io": 3,
    "late3f_position": 8,
    "late3f_gap": 5,
    "late3f_io": 3,
    "goal_position": 8,
    "goal_gap": 5,
    "goal_io": 3,
    "start_index": 50.0,
    "gate_miss_rate": 5.0,
    "upset_index": 50,
    "speed_balance": 0.0,
    "position_delta": 0.0,
    "io_shift": 0.0,
    "log_odds": 2.3,
    "risk_score": 0.5,
    "race_head_count": 16,
    # === Phase 1-A 追加 ===
    "jockey_win_rate": 8.0,
    "jockey_top2_rate": 16.0,
    "jockey_top3_rate": 25.0,
    "stable_rank": 5,
    "gekisou_index": 50,
    "gekisou_rank": 8,
    "rising_grade": 3,
    "rotation_days": 28,
    "tei_code": 0,
    "class_code": 0,
    "condition_class": 0,
    "body_weight": 480,
    "body_weight_delta": 0.0,
    "ls_rank": 8,
    "ten_rank": 8,
    "pace_rank": 8,
    "agari_rank": 8,
    "position_rank": 8,
    "nyukyu_run_count": 5,
    "nyukyu_days_ago": 14,
    "total_prize": 100,
    "earned_prize": 50,
    "distance_aptitude_2": 3,
    "upset_marker": 0,
    "popularity_index": 50,
    "ref_prev_run": 0,
    # === Phase 1-B 追加 (race-relative derived) ===
    "idm_rank_in_race": 8,
    "idm_z_in_race": 0.0,
    "overall_rank_in_race": 8,
    "overall_z_in_race": 0.0,
    "jockey_rank_in_race": 8,
    "jockey_z_in_race": 0.0,
    "ten_rank_in_race": 8,
    "ten_z_in_race": 0.0,
    "agari_rank_in_race": 8,
    "agari_z_in_race": 0.0,
    "position_rank_in_race": 8,
    "position_z_in_race": 0.0,
    "odds_share": 0.06,
    "popularity_z_in_race": 0.0,
}


def preprocess_features(df: pd.DataFrame) -> pd.DataFrame:
    """Fill missing values and cast types. Mirrors src/features/engineering.preprocess()."""
    df = df.copy()
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("Unknown").astype(str)
    for col, default in NUMERICAL_DEFAULTS.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)
    return df


def create_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived features. Mirrors src/features/derived.add_derived_features()."""
    df = df.copy()
    if "ten_index" in df.columns and "agari_index" in df.columns:
        df["speed_balance"] = df["ten_index"] - df["agari_index"]
    if "goal_position" in df.columns and "mid_position" in df.columns:
        df["position_delta"] = df["goal_position"] - df["mid_position"]
    if "goal_io" in df.columns and "mid_position_io" in df.columns:
        df["io_shift"] = df["goal_io"] - df["mid_position_io"]
    if "odds" in df.columns:
        df["log_odds"] = np.log(df["odds"].clip(lower=1.0))
    if "gate_miss_rate" in df.columns and "start_index" in df.columns:
        df["risk_score"] = df["gate_miss_rate"] * (1 - df["start_index"] / 10)
    return df


# --- Modal Functions ---

@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=21600,  # 6h hard cap (Phase 1-C: long training tolerated)
    memory=16384,
    cpu=8.0,
)
def train_model(
    training_data_csv: str,
    model_name: str = "jrdb_predictor",
    time_limit: int = 7200,
    presets: str = "best_quality",
    excluded_model_types: list[str] | None = None,
    hyperparameters: dict | None = None,
) -> dict:
    """Train an AutoGluon model on JRDB feature data.

    Phase 1-C defaults: best_quality preset, GBM/CAT/XGB/FASTAI explicit
    hyperparameters (RF/KNN excluded — slow on tabular at this scale).
    """
    from autogluon.tabular import TabularPredictor

    df = pd.read_csv(StringIO(training_data_csv))
    df = preprocess_features(df)
    df = create_derived_features(df)

    label = "is_place"
    if label not in df.columns:
        return {"success": False, "error": f"Label column '{label}' not found"}

    df = df.dropna(subset=[label])
    print(f"Training with {len(df)} samples, {len(df.columns)} columns")

    # race_key / finish_order are metadata for per-race metrics, not features.
    has_race_key = "race_key" in df.columns
    ignored_columns: list[str] = []
    if has_race_key:
        ignored_columns.append("race_key")
    if "finish_order" in df.columns:
        ignored_columns.append("finish_order")

    model_path = os.path.join(VOLUME_PATH, model_name)
    predictor = TabularPredictor(
        label=label,
        path=model_path,
        problem_type="binary",
        eval_metric="roc_auc",
    )

    if hyperparameters is None:
        # Phase 1-C: explicit gradient-boosting + NN portfolio.
        # AutoGluon stacks/bags these under best_quality. RF/KNN excluded.
        hyperparameters = {
            "GBM": [
                {},
                {"extra_trees": True, "ag_args": {"name_suffix": "XT"}},
            ],
            "CAT": {},
            "XGB": {},
            "FASTAI": {},
        }
    if excluded_model_types is None:
        excluded_model_types = ["RF", "KNN"]

    fit_kwargs = {
        "train_data": df,
        "time_limit": time_limit,
        "presets": presets,
        "hyperparameters": hyperparameters,
        "excluded_model_types": excluded_model_types,
    }
    if ignored_columns:
        fit_kwargs["ignored_columns"] = ignored_columns

    fit_start = time.time()
    predictor.fit(**fit_kwargs)
    train_time_seconds = int(time.time() - fit_start)

    # Phase 1-D: OOF metrics — Brier / Hit@3 / ECE on out-of-fold predictions.
    brier_score = None
    hit_at_3 = None
    ece = None
    try:
        oof = predictor.get_oof_pred_proba()
        if isinstance(oof, pd.DataFrame) and 1 in oof.columns:
            oof_probs = oof[1].to_numpy()
        else:
            oof_probs = (
                oof.to_numpy() if isinstance(oof, pd.Series) else oof.iloc[:, -1].to_numpy()
            )
        y_true = df[label].to_numpy().astype(float)

        # Brier score
        brier_score = float(((y_true - oof_probs) ** 2).mean())

        # ECE (10 equal-width bins)
        bins = [i / 10 for i in range(11)]
        ece_val = 0.0
        n = len(y_true)
        for b in range(10):
            lo = bins[b]
            hi = bins[b + 1] if b < 9 else bins[b + 1] + 1e-9
            mask = (oof_probs >= lo) & (oof_probs < hi)
            if mask.any():
                weight = mask.sum() / n
                ece_val += weight * abs(
                    float(y_true[mask].mean()) - float(oof_probs[mask].mean())
                )
        ece = float(ece_val)

        # Hit@3 — needs race_key
        if has_race_key:
            tmp = pd.DataFrame({
                "race_key": df["race_key"].to_numpy(),
                "p": oof_probs,
                "y": y_true,
            })
            hits = 0
            races = 0
            for _, group in tmp.groupby("race_key"):
                races += 1
                top3 = group.nlargest(3, "p")
                if (top3["y"] == 1).any():
                    hits += 1
            hit_at_3 = (hits / races) if races else None
    except Exception as exc:
        print(f"OOF metrics failed (non-fatal): {exc}")

    try:
        leaderboard = predictor.leaderboard(silent=True, extra_info=True)
    except TypeError:
        leaderboard = predictor.leaderboard(silent=True)

    best_score = float(leaderboard["score_val"].max()) if len(leaderboard) > 0 else None
    best_model = leaderboard.iloc[0]["model"] if len(leaderboard) > 0 else "unknown"
    leaderboard_records = json.loads(leaderboard.to_json(orient="records"))

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "num_samples": len(df),
        "presets": presets,
        "best_model": str(best_model),
        "best_score": best_score,
        "train_time_seconds": train_time_seconds,
        "eval_metric": "roc_auc",
        "brier": brier_score,
        "hit_at_3": hit_at_3,
        "ece": ece,
    }
    metadata_path = os.path.join(VOLUME_PATH, model_name, "metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f)

    leaderboard_path = os.path.join(VOLUME_PATH, model_name, "leaderboard.json")
    with open(leaderboard_path, "w") as f:
        json.dump(leaderboard_records, f)

    model_volume.commit()

    return {
        "success": True,
        "model_path": model_path,
        "num_samples": len(df),
        "presets_used": presets,
        "best_model": str(best_model),
        "best_score": best_score,
        "trained_at": metadata["trained_at"],
        "train_time_seconds": train_time_seconds,
        "leaderboard": leaderboard_records,
        "eval_metric": "roc_auc",
        "brier": brier_score,
        "hit_at_3": hit_at_3,
        "ece": ece,
    }


# --- Phase 2: LightGBM lambdarank ---

@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=21600,
    memory=16384,
    cpu=8.0,
)
def train_lambdarank(
    training_data_csv: str,
    model_name: str = "jrdb_ranker",
    num_boost_round: int = 3000,
    learning_rate: float = 0.05,
    early_stopping_rounds: int = 100,
) -> dict:
    """Train a LightGBM lambdarank model on per-race ranking labels.

    Requires ``race_key`` and ``finish_order`` columns. Each race forms a query
    group. Label = ``max(0, 17 - finish_order)`` (gain-based).

    After training, fits a softmax temperature on the validation set that
    minimizes NLL of actual winners. Stored in metadata for predict-time use.
    """
    import lightgbm as lgb
    import numpy as np

    df = pd.read_csv(StringIO(training_data_csv))
    df = preprocess_features(df)
    df = create_derived_features(df)

    if "race_key" not in df.columns:
        return {"success": False, "error": "race_key column required"}
    if "finish_order" not in df.columns:
        return {"success": False, "error": "finish_order column required"}

    df = df.dropna(subset=["finish_order"])
    df = df[df["finish_order"] > 0]
    df = df.sort_values(["race_key"]).reset_index(drop=True)

    df["lambda_label"] = (
        (17 - df["finish_order"].clip(upper=17)).clip(lower=0).astype(int)
    )

    # Feature columns = everything except meta/label
    meta_cols = {"race_key", "finish_order", "lambda_label", "is_place"}
    feature_cols = [c for c in df.columns if c not in meta_cols]

    # Cast categoricals
    cat_cols_present = [c for c in CATEGORICAL_COLS if c in feature_cols]
    X = df[feature_cols].copy()
    for c in cat_cols_present:
        X[c] = X[c].astype("category")
    y = df["lambda_label"]

    # Race-key based split: last 10% of unique race_keys = validation
    unique_keys = df["race_key"].drop_duplicates().tolist()
    cutoff = int(len(unique_keys) * 0.9)
    val_keys = set(unique_keys[cutoff:])
    val_mask = df["race_key"].isin(val_keys).to_numpy()
    train_mask = ~val_mask

    train_groups = df.loc[train_mask].groupby("race_key", sort=False).size().tolist()
    val_groups = df.loc[val_mask].groupby("race_key", sort=False).size().tolist()

    train_data = lgb.Dataset(
        X.loc[train_mask], y.loc[train_mask], group=train_groups,
        categorical_feature=cat_cols_present,
        free_raw_data=False,
    )
    val_data = lgb.Dataset(
        X.loc[val_mask], y.loc[val_mask], group=val_groups,
        categorical_feature=cat_cols_present,
        reference=train_data,
        free_raw_data=False,
    )

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": [1, 3],
        "lambdarank_truncation_level": 3,
        "learning_rate": learning_rate,
        "num_leaves": 63,
        "min_data_in_leaf": 50,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
    }

    fit_start = time.time()
    model = lgb.train(
        params,
        train_data,
        num_boost_round=num_boost_round,
        valid_sets=[val_data],
        valid_names=["val"],
        callbacks=[
            lgb.early_stopping(early_stopping_rounds, verbose=False),
            lgb.log_evaluation(period=200),
        ],
    )
    train_time_seconds = int(time.time() - fit_start)

    # Save model + config
    model_path = os.path.join(VOLUME_PATH, model_name)
    os.makedirs(model_path, exist_ok=True)
    model.save_model(os.path.join(model_path, "model.txt"))
    with open(os.path.join(model_path, "feature_cols.json"), "w") as f:
        json.dump(
            {"feature_cols": feature_cols, "categorical_cols": cat_cols_present},
            f,
        )

    # Compute scores on validation, fit temperature
    val_X = X.loc[val_mask]
    val_scores = np.asarray(model.predict(val_X))
    val_df = df.loc[val_mask, ["race_key", "finish_order"]].copy()
    val_df["score"] = val_scores

    grid = (0.3, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 5.0)
    best_T = 1.0
    best_nll = float("inf")
    ndcg1 = 0
    n_races = 0
    for race_key, group in val_df.groupby("race_key"):
        n_races += 1
        scores = group["score"].to_numpy()
        if (group["finish_order"] == 1).any():
            top_idx = int(scores.argmax())
            actual_winner_pos = int(group.iloc[top_idx]["finish_order"])
            if actual_winner_pos == 1:
                ndcg1 += 1
    hit_at_1 = ndcg1 / n_races if n_races else None

    for T in grid:
        nll = 0.0
        n = 0
        for race_key, group in val_df.groupby("race_key"):
            scores = group["score"].to_numpy() / T
            scores = scores - scores.max()
            probs = np.exp(scores)
            probs = probs / probs.sum()
            winner_rows = group[group["finish_order"] == 1]
            if winner_rows.empty:
                continue
            winner_idx = int((group["finish_order"].values == 1).argmax())
            p = max(float(probs[winner_idx]), 1e-12)
            nll -= float(np.log(p))
            n += 1
        if n == 0:
            continue
        nll /= n
        if nll < best_nll:
            best_nll = nll
            best_T = float(T)

    best_iteration = int(model.best_iteration or num_boost_round)
    val_ndcg_at_3 = None
    try:
        val_ndcg_at_3 = float(model.best_score["val"].get("ndcg@3"))
    except (KeyError, AttributeError, TypeError):
        pass

    metadata = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "model_type": "lightgbm_lambdarank",
        "num_samples": len(df),
        "num_races": int(df["race_key"].nunique()),
        "best_iteration": best_iteration,
        "optimal_temperature": best_T,
        "validation_nll": (
            float(best_nll) if best_nll != float("inf") else None
        ),
        "validation_ndcg_at_3": val_ndcg_at_3,
        "validation_hit_at_1": hit_at_1,
        "feature_cols": feature_cols,
        "train_time_seconds": train_time_seconds,
    }
    with open(os.path.join(model_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)
    model_volume.commit()

    return {
        "success": True,
        "model_path": model_path,
        "model_type": "lightgbm_lambdarank",
        "num_samples": metadata["num_samples"],
        "num_races": metadata["num_races"],
        "best_iteration": best_iteration,
        "optimal_temperature": best_T,
        "validation_nll": metadata["validation_nll"],
        "validation_ndcg_at_3": val_ndcg_at_3,
        "validation_hit_at_1": hit_at_1,
        "trained_at": metadata["trained_at"],
        "train_time_seconds": train_time_seconds,
    }


def _pl_top_k_probs(prob_win: list[float]) -> tuple[list[float], list[float]]:
    """Plackett-Luce: from P(win), derive P(top2) and P(top3) per horse.

    Uses ``v_i = prob_win_i`` (already normalized) as PL parameters.
    O(N^3) enumeration — fine for N ≤ 18.
    """
    import numpy as np

    v = np.asarray(prob_win, dtype=float)
    N = len(v)
    S = float(v.sum())
    if S <= 0:
        return [0.0] * N, [0.0] * N

    p_top2 = np.zeros(N)
    p_top3 = np.zeros(N)
    for i in range(N):
        # P(i = 1)
        p1 = v[i] / S
        p_top2[i] += p1
        p_top3[i] += p1
        # P(i = 2)
        p2 = 0.0
        for j in range(N):
            if j == i:
                continue
            denom = S - v[j]
            if denom > 0:
                p2 += (v[j] / S) * (v[i] / denom)
        p_top2[i] += p2
        p_top3[i] += p2
        # P(i = 3)
        p3 = 0.0
        for j in range(N):
            if j == i:
                continue
            denom1 = S - v[j]
            if denom1 <= 0:
                continue
            for k in range(N):
                if k == i or k == j:
                    continue
                denom2 = denom1 - v[k]
                if denom2 > 0:
                    p3 += (v[j] / S) * (v[k] / denom1) * (v[i] / denom2)
        p_top3[i] += p3

    return [float(x) for x in p_top2], [float(x) for x in p_top3]


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def predict_lambdarank(
    features_json: str,
    model_name: str = "jrdb_ranker",
) -> dict:
    """Predict lambdarank scores for one race; return P(win)/P(top2)/P(top3).

    Input: JSON list of horse-records for one race.
    Output: success, scores, prob_win, prob_top2, prob_top3, temperature.
    """
    import lightgbm as lgb
    import numpy as np

    try:
        model_path = os.path.join(VOLUME_PATH, model_name)
        model = lgb.Booster(model_file=os.path.join(model_path, "model.txt"))
        with open(os.path.join(model_path, "feature_cols.json")) as f:
            cfg = json.load(f)
        with open(os.path.join(model_path, "metadata.json")) as f:
            meta = json.load(f)
        T = float(meta.get("optimal_temperature", 1.0))

        features = json.loads(features_json)
        df = pd.DataFrame(features)
        df = preprocess_features(df)
        df = create_derived_features(df)

        feature_cols = cfg["feature_cols"]
        for c in feature_cols:
            if c not in df.columns:
                df[c] = NUMERICAL_DEFAULTS.get(c, 0)
        for c in cfg["categorical_cols"]:
            if c in df.columns:
                df[c] = df[c].astype("category")
        X = df[feature_cols]

        scores = np.asarray(model.predict(X), dtype=float)

        s = scores / T
        s = s - s.max()
        prob_win = np.exp(s)
        prob_win = prob_win / prob_win.sum()

        prob_top2, prob_top3 = _pl_top_k_probs([float(p) for p in prob_win])

        return {
            "success": True,
            "scores": [float(s) for s in scores],
            "prob_win": [float(p) for p in prob_win],
            "prob_top2": prob_top2,
            "prob_top3": prob_top3,
            "temperature": T,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def predict(
    features_json: str,
    model_name: str = "jrdb_predictor",
) -> dict:
    """Predict is_place probabilities for given features."""
    from autogluon.tabular import TabularPredictor

    try:
        model_path = os.path.join(VOLUME_PATH, model_name)
        predictor = TabularPredictor.load(
            model_path, require_py_version_match=False,
        )

        features = json.loads(features_json)
        df = pd.DataFrame(features)
        df = preprocess_features(df)
        df = create_derived_features(df)

        proba = predictor.predict_proba(df)
        if isinstance(proba, pd.DataFrame) and 1 in proba.columns:
            predictions = proba[1].tolist()
        else:
            predictions = proba.iloc[:, -1].tolist()

        return {"success": True, "predictions": predictions}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=30,
)
def get_model_status(model_name: str = "jrdb_predictor") -> dict:
    """Check if a trained model exists on the volume."""
    model_path = os.path.join(VOLUME_PATH, model_name)

    if not os.path.exists(model_path):
        return {"exists": False, "model_name": model_name}

    files = os.listdir(model_path)
    predictor_exists = "predictor.pkl" in files

    metadata = None
    metadata_path = os.path.join(model_path, "metadata.json")
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            metadata = json.load(f)

    return {
        "exists": True,
        "model_name": model_name,
        "files": files,
        "predictor_exists": predictor_exists,
        "trained_at": metadata.get("trained_at") if metadata else None,
        "best_score": metadata.get("best_score") if metadata else None,
        "num_samples": metadata.get("num_samples") if metadata else None,
    }


@app.function(
    image=autogluon_image,
    volumes={VOLUME_PATH: model_volume},
    timeout=60,
    memory=4096,
)
def get_feature_importance(model_name: str = "jrdb_predictor") -> dict:
    """Get feature importance from a trained model."""
    from autogluon.tabular import TabularPredictor

    try:
        model_path = os.path.join(VOLUME_PATH, model_name)
        predictor = TabularPredictor.load(
            model_path, require_py_version_match=False,
        )
        importance_df = predictor.feature_importance()

        features = []
        for name, row in importance_df.iterrows():
            imp = row["importance"] if "importance" in row.index else row.iloc[0]
            features.append({"name": str(name), "importance": float(imp)})

        features.sort(key=lambda x: x["importance"], reverse=True)
        return {"success": True, "features": features}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Local Entrypoints ---

@app.local_entrypoint()
def test_status():
    """Check model status."""
    result = get_model_status.remote()
    print(f"Model status: {result}")


@app.local_entrypoint()
def test_train():
    """Run a quick test training."""
    import pathlib
    csv_path = pathlib.Path("data/processed/training.csv")
    if not csv_path.exists():
        print(f"Training data not found at {csv_path}")
        return
    csv_data = csv_path.read_text()
    result = train_model.remote(
        training_data_csv=csv_data,
        time_limit=300,
        presets="medium_quality",
    )
    print(f"Training result: {result}")
