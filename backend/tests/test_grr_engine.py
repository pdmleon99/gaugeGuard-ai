"""GR&R engine tests."""
from __future__ import annotations

import pytest
import pandas as pd

from app.engines.grr_engine import run_grr_anova, run_grr_range


def test_grr_pass_acceptable(sample_df_grr_pass, default_thresholds):
    result = run_grr_anova(sample_df_grr_pass, "TEST-EQ", default_thresholds)
    assert result.status == "ACCEPTABLE"
    assert result.percent_grr < 10.0
    assert result.ndc >= 5


def test_grr_fail_not_acceptable(sample_df_grr_fail, default_thresholds):
    result = run_grr_anova(sample_df_grr_fail, "TEST-EQ", default_thresholds)
    assert result.status == "NOT_ACCEPTABLE"
    assert result.percent_grr > 30.0


def test_grr_marginal(sample_df_grr_marginal, default_thresholds):
    result = run_grr_anova(sample_df_grr_marginal, "TEST-EQ", default_thresholds)
    assert result.status == "MARGINAL"
    assert 10.0 <= result.percent_grr <= 30.0


def test_missing_column_raises():
    df = pd.DataFrame({
        "part_id": [1, 2],
        "operator_id": [1, 1],
        "measurement_value": [1.0, 1.1],
    })
    with pytest.raises(ValueError, match="Missing columns"):
        run_grr_anova(df, "EQ", {})


def test_nan_raises(sample_df_grr_pass):
    df = sample_df_grr_pass.copy()
    df.loc[0, "measurement_value"] = float("nan")
    with pytest.raises(ValueError, match="NaN"):
        run_grr_anova(df, "EQ", {})


def test_ndc_formula(sample_df_grr_pass, default_thresholds):
    result = run_grr_anova(sample_df_grr_pass, "EQ", default_thresholds)
    import math
    expected_ndc = int(math.floor(1.41 * result.pv_study / result.grr_study))
    assert result.ndc == expected_ndc


def test_anova_and_range_agree(sample_df_grr_pass, default_thresholds):
    r_anova = run_grr_anova(sample_df_grr_pass, "EQ", default_thresholds)
    r_range = run_grr_range(sample_df_grr_pass, "EQ", default_thresholds)
    assert abs(r_anova.percent_grr - r_range.percent_grr) < 5.0


def test_variance_components_sum(sample_df_grr_pass, default_thresholds):
    result = run_grr_anova(sample_df_grr_pass, "EQ", default_thresholds)
    tv_reconstructed = (result.grr_study ** 2 + result.pv_study ** 2) ** 0.5
    assert abs(tv_reconstructed - result.tv_study) < 0.001


def test_percent_grr_quadrature(sample_df_grr_pass, default_thresholds):
    result = run_grr_anova(sample_df_grr_pass, "EQ", default_thresholds)
    grr_reconstructed = (result.percent_ev ** 2 + result.percent_av ** 2) ** 0.5
    assert abs(grr_reconstructed - result.percent_grr) < 0.1


def test_too_few_trials_raises():
    # 2 parts, 2 operators, but only 1 trial per cell → should raise
    df = pd.DataFrame({
        "part_id": ["P01", "P01", "P02", "P02"],
        "operator_id": ["OP1", "OP2", "OP1", "OP2"],
        "trial": [1, 1, 1, 1],
        "measurement_value": [25.0, 25.1, 25.05, 25.15],
    })
    with pytest.raises(ValueError, match="Minimum 2 trials"):
        run_grr_anova(df, "EQ", {})


def test_range_method_pass(sample_df_grr_pass, default_thresholds):
    result = run_grr_range(sample_df_grr_pass, "EQ", default_thresholds)
    assert result.status == "ACCEPTABLE"
    assert result.method == "Range"
    assert result.anova_table is None
