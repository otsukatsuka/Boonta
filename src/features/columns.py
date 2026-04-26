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
    "基準人気順位": "popularity",
    "負担重量": "weight_carried",
    # === Phase 1-A 追加: 騎手・調教・厩舎関連 ===
    "騎手期待単勝率": "jockey_win_rate",
    "騎手期待連対率": "jockey_top2_rate",
    "騎手期待3着内率": "jockey_top3_rate",
    "厩舎ランク": "stable_rank",
    "厩舎評価コード": "stable_eval_code",
    "調教矢印コード": "training_arrow_code",
    # === Phase 1-A 追加: 数値指標 ===
    "激走指数": "gekisou_index",
    "激走順位": "gekisou_rank",
    "上昇度": "rising_grade",
    "ローテーション": "rotation_days",
    "蹄コード": "tei_code",
    "クラスコード": "class_code",
    "条件クラス": "condition_class",
    "枠確定馬体重": "body_weight",
    "LS指数順位": "ls_rank",
    "テン指数順位": "ten_rank",
    "ペース指数順位": "pace_rank",
    "上がり指数順位": "agari_rank",
    "位置指数順位": "position_rank",
    "入厩何走目": "nyukyu_run_count",
    "入厩何日前": "nyukyu_days_ago",
    "獲得賞金": "total_prize",
    "収得賞金": "earned_prize",
    "距離適性2": "distance_aptitude_2",
    "万券印": "upset_marker",
    "人気指数": "popularity_index",
    "参考前走": "ref_prev_run",
    # === Phase 1-A 追加: 印・カテゴリカル (JRDB 9 段階印) ===
    "総合印": "marker_overall",
    "IDM印": "marker_idm",
    "情報印": "marker_info",
    "騎手印": "marker_jockey",
    "厩舎印": "marker_stable",
    "調教印": "marker_training",
    "激走印": "marker_gekisou",
    "芝適性コード": "turf_aptitude",
    "ダ適性コード": "dirt_aptitude",
    # === Phase 1-A 追加: 属性・状態 ===
    "ブリンカー": "blinker",
    "性別コード": "sex_code",
    "馬記号コード": "horse_mark_code",
    "見習い区分": "apprentice",
    "輸送区分": "transport",
    "降級フラグ": "demotion_flag",
    "激走タイプ": "gekisou_type",
    "休養理由分類コード": "rest_reason",
    "放牧先ランク": "pasture_rank",
    # === Phase 1-A 追加: 走法・体型・特記 (raw text categorical) ===
    "走法": "running_form",
    "体型": "body_shape",
    "体型総合1": "body_summary_1",
    "体型総合2": "body_summary_2",
    "体型総合3": "body_summary_3",
    "馬特記1": "horse_remark_1",
    "馬特記2": "horse_remark_2",
    "馬特記3": "horse_remark_3",
    "フラグ": "kyi_flags",
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
    # 派生フィーチャー (existing)
    "speed_balance", "position_delta", "io_shift", "log_odds", "risk_score",
    "race_head_count",
    # === Phase 1-A 追加 ===
    # 騎手・調教・厩舎
    "jockey_win_rate", "jockey_top2_rate", "jockey_top3_rate",
    "stable_rank", "stable_eval_code", "training_arrow_code",
    # 数値指標
    "gekisou_index", "gekisou_rank", "rising_grade", "rotation_days",
    "tei_code", "class_code", "condition_class",
    "body_weight", "body_weight_delta",
    "ls_rank", "ten_rank", "pace_rank", "agari_rank", "position_rank",
    "nyukyu_run_count", "nyukyu_days_ago",
    "total_prize", "earned_prize", "distance_aptitude_2",
    "upset_marker", "popularity_index", "ref_prev_run",
    # 印 categorical (9 段階 + 無印)
    "marker_overall", "marker_idm", "marker_info", "marker_jockey",
    "marker_stable", "marker_training", "marker_gekisou",
    "turf_aptitude", "dirt_aptitude",
    # 属性
    "blinker", "sex_code", "horse_mark_code", "apprentice", "transport",
    "demotion_flag", "gekisou_type", "rest_reason", "pasture_rank",
    # 走法・体型・特記 (raw text)
    "running_form", "body_shape",
    "body_summary_1", "body_summary_2", "body_summary_3",
    "horse_remark_1", "horse_remark_2", "horse_remark_3",
    "kyi_flags",
    # === Phase 1-B 追加: race-relative derived (filled in features/derived.py) ===
    "idm_rank_in_race", "idm_z_in_race",
    "overall_rank_in_race", "overall_z_in_race",
    "jockey_rank_in_race", "jockey_z_in_race",
    "ten_rank_in_race", "ten_z_in_race",
    "agari_rank_in_race", "agari_z_in_race",
    "position_rank_in_race", "position_z_in_race",
    "odds_share", "popularity_z_in_race",
]

# Categorical features (AutoGluon handles these as categories)
CATEGORICAL_FEATURES: list[str] = [
    "pace_forecast", "tenkai_symbol", "running_style",
    "distance_aptitude", "heavy_track_code",
    # === Phase 1-A 追加 ===
    # 印
    "marker_overall", "marker_idm", "marker_info", "marker_jockey",
    "marker_stable", "marker_training", "marker_gekisou",
    "turf_aptitude", "dirt_aptitude",
    # 属性 (low-cardinality codes)
    "blinker", "sex_code", "horse_mark_code", "apprentice", "transport",
    "demotion_flag", "gekisou_type", "rest_reason", "pasture_rank",
    "stable_eval_code", "training_arrow_code",
    # 走法・体型・特記 (high-card text — AutoGluon will treat as category)
    "running_form", "body_shape",
    "body_summary_1", "body_summary_2", "body_summary_3",
    "horse_remark_1", "horse_remark_2", "horse_remark_3",
    "kyi_flags",
]

# Numerical feature defaults (used to fill NaN)
NUMERICAL_DEFAULTS: dict[str, float] = {
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
    # === Phase 1-B 追加 ===
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

# Label column
LABEL_COLUMN = "is_place"
