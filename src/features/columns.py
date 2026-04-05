"""Feature column definitions, categories, and default values."""
from __future__ import annotations

# Mapping from JRDB field names to ML feature names
FIELD_TO_FEATURE: dict[str, str] = {
    # 展開コア (KYI)
    "ペース予想": "pace_forecast",
    "道中順位": "mid_position",
    "道中差": "mid_gap",
    "道中内外": "mid_position_io",
    "後3F順位": "late3f_position",
    "後3F差": "late3f_gap",
    "後3F内外": "late3f_io",
    "ゴール順位": "goal_position",
    "ゴール差": "goal_gap",
    "ゴール内外": "goal_io",
    "展開記号": "tenkai_symbol",
    # スピード指標 (KYI)
    "テン指数": "ten_index",
    "ペース指数": "pace_index",
    "上がり指数": "agari_index",
    "位置指数": "position_index",
    "IDM": "idm",
    # 馬・厩舎・騎手指数 (KYI)
    "騎手指数": "jockey_index",
    "情報指数": "info_index",
    "総合指数": "overall_index",
    "調教指数": "training_index",
    "厩舎指数": "stable_index",
    # 適性・リスク (KYI)
    "脚質": "running_style",
    "距離適性": "distance_aptitude",
    "重適正コード": "heavy_track_code",
    "馬スタート指数": "start_index",
    "馬出遅率": "gate_miss_rate",
    "万券指数": "upset_index",
    # レース条件
    "馬番": "horse_number",
    "枠番": "waku",
    "基準オッズ": "odds",
    "基準���気順位": "popularity",
    "負担重量": "weight_carried",
}

# All ML feature column names (order matters for training/prediction consistency)
FEATURE_COLUMNS: list[str] = [
    # 展開コア
    "pace_forecast", "mid_position", "mid_gap", "mid_position_io",
    "late3f_position", "late3f_gap", "late3f_io",
    "goal_position", "goal_gap", "goal_io", "tenkai_symbol",
    # スピード指標
    "ten_index", "pace_index", "agari_index", "position_index", "idm",
    # 馬・厩舎・騎手
    "jockey_index", "info_index", "overall_index", "training_index", "stable_index",
    # 適性・リスク
    "running_style", "distance_aptitude", "heavy_track_code",
    "start_index", "gate_miss_rate", "upset_index",
    # レース条件
    "horse_number", "waku", "odds", "popularity", "weight_carried",
    # 派生フィーチャー
    "speed_balance", "position_delta", "io_shift", "log_odds", "risk_score",
    "race_head_count",
]

# Categorical features (AutoGluon handles these as categories)
CATEGORICAL_FEATURES: list[str] = [
    "pace_forecast", "tenkai_symbol", "running_style",
    "distance_aptitude", "heavy_track_code",
]

# Numerical feature defaults (used to fill NaN)
NUMERICAL_DEFAULTS: dict[str, float] = {
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
}

# Label column
LABEL_COLUMN = "is_place"
