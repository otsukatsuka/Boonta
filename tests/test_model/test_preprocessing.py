"""Tests for Modal functions preprocessing logic.

Tests the inline preprocessing that mirrors src/features/ logic.
AutoGluon is NOT imported - only preprocessing functions are tested.
"""
import numpy as np
import pandas as pd

from src.model.functions import (
    CATEGORICAL_COLS,
    NUMERICAL_DEFAULTS,
    create_derived_features,
    preprocess_features,
)


class TestPreprocessFeatures:
    def test_fills_categorical_nan(self):
        df = pd.DataFrame({"pace_forecast": [None, "M", None]})
        result = preprocess_features(df)
        assert result["pace_forecast"].tolist() == ["Unknown", "M", "Unknown"]

    def test_fills_numerical_nan(self):
        df = pd.DataFrame({"idm": [None, 52.3], "odds": [None, 5.0]})
        result = preprocess_features(df)
        assert result["idm"].iloc[0] == 50.0
        assert result["odds"].iloc[0] == 10.0

    def test_preserves_existing_values(self):
        df = pd.DataFrame({"idm": [60.0], "pace_forecast": ["H"]})
        result = preprocess_features(df)
        assert result["idm"].iloc[0] == 60.0
        assert result["pace_forecast"].iloc[0] == "H"

    def test_all_numerical_defaults_covered(self):
        """Every non-categorical FEATURE_COLUMNS entry has a NUMERICAL_DEFAULT.

        Derived dynamically from src/features/columns.py so adding a feature
        there forces it to appear here too (no hardcoded list to update).
        """
        from src.features.columns import (
            CATEGORICAL_FEATURES,
            FEATURE_COLUMNS,
        )

        expected_numeric = {c for c in FEATURE_COLUMNS if c not in CATEGORICAL_FEATURES}
        missing = expected_numeric - set(NUMERICAL_DEFAULTS.keys())
        assert not missing, f"Missing defaults for: {sorted(missing)}"

    def test_categorical_cols_match(self):
        """Modal CATEGORICAL_COLS must match src/features/columns.py."""
        from src.features.columns import CATEGORICAL_FEATURES as SRC_CATS

        assert CATEGORICAL_COLS == SRC_CATS

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"idm": [None]})
        _ = preprocess_features(df)
        assert df["idm"].iloc[0] is None


class TestCreateDerivedFeatures:
    def test_speed_balance(self):
        df = pd.DataFrame({"ten_index": [48.5], "agari_index": [53.1]})
        result = create_derived_features(df)
        assert abs(result["speed_balance"].iloc[0] - (-4.6)) < 0.01

    def test_position_delta(self):
        df = pd.DataFrame({"goal_position": [1.0], "mid_position": [5.0]})
        result = create_derived_features(df)
        assert result["position_delta"].iloc[0] == -4.0

    def test_io_shift(self):
        df = pd.DataFrame({"goal_io": [2.0], "mid_position_io": [4.0]})
        result = create_derived_features(df)
        assert result["io_shift"].iloc[0] == -2.0

    def test_log_odds(self):
        df = pd.DataFrame({"odds": [10.0]})
        result = create_derived_features(df)
        assert abs(result["log_odds"].iloc[0] - np.log(10.0)) < 0.01

    def test_log_odds_clips_low(self):
        """Odds below 1.0 should be clipped to 1.0 before log."""
        df = pd.DataFrame({"odds": [0.5]})
        result = create_derived_features(df)
        assert result["log_odds"].iloc[0] == 0.0  # log(1.0) = 0

    def test_risk_score(self):
        df = pd.DataFrame({"gate_miss_rate": [10.0], "start_index": [5.0]})
        result = create_derived_features(df)
        expected = 10.0 * (1 - 5.0 / 10)  # = 5.0
        assert abs(result["risk_score"].iloc[0] - expected) < 0.01

    def test_missing_columns_no_error(self):
        """Derived features should not fail if source columns are missing."""
        df = pd.DataFrame({"some_col": [1, 2, 3]})
        result = create_derived_features(df)
        assert "speed_balance" not in result.columns

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"ten_index": [48.5], "agari_index": [53.1]})
        original_cols = list(df.columns)
        _ = create_derived_features(df)
        assert list(df.columns) == original_cols


class TestPreprocessingSync:
    """Verify that Modal preprocessing matches src/features/ logic."""

    def test_defaults_match_src(self):
        """Modal NUMERICAL_DEFAULTS should match src/features/columns.py."""
        from src.features.columns import NUMERICAL_DEFAULTS as SRC_DEFAULTS
        assert NUMERICAL_DEFAULTS == SRC_DEFAULTS

    def test_categorical_match_src(self):
        """Modal CATEGORICAL_COLS should match src/features/columns.py."""
        from src.features.columns import CATEGORICAL_FEATURES as SRC_CATS
        assert CATEGORICAL_COLS == SRC_CATS
