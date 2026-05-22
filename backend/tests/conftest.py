"""Pytest fixtures for GaugeGuard AI tests."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

SAMPLES = Path(__file__).parent.parent.parent / "data" / "samples"


def _load(name: str) -> pd.DataFrame:
    p = SAMPLES / f"{name}.csv"
    if not p.exists():
        pytest.skip(f"Sample file not found: {p}")
    return pd.read_csv(p)


@pytest.fixture
def sample_df_grr_pass():
    return _load("grr_pass")


@pytest.fixture
def sample_df_grr_fail():
    return _load("grr_fail")


@pytest.fixture
def sample_df_grr_marginal():
    return _load("grr_marginal")


@pytest.fixture
def spc_df_stable():
    return _load("spc_stable")


@pytest.fixture
def spc_df_shift():
    return _load("spc_shift")


@pytest.fixture
def spc_df_drift():
    return _load("spc_drift")


@pytest.fixture
def spc_df_anomalies():
    return _load("spc_anomalies")


@pytest.fixture
def default_thresholds():
    return {
        "grr_acceptable_pct": 10.0,
        "grr_marginal_pct": 30.0,
        "ndc_minimum": 5,
        "study_k": 6,
        "alpha_interaction": 0.25,
    }
