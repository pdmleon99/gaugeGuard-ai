"""GR&R Engine — ANOVA and Range methods per AIAG MSA 4th Edition."""
from __future__ import annotations

import math
import time
import uuid
import warnings
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import f as f_dist

# ---------------------------------------------------------------------------
# d2* lookup table (AIAG MSA 4th Ed, Table D3)
# ---------------------------------------------------------------------------
D2_STAR: dict[tuple[int, int], float] = {
    (2, 2): 1.41, (3, 2): 1.91, (4, 2): 2.24, (5, 2): 2.48, (6, 2): 2.67,
    (7, 2): 2.83, (8, 2): 2.96, (9, 2): 3.08, (10, 2): 3.18, (11, 2): 3.27,
    (12, 2): 3.35, (13, 2): 3.42, (14, 2): 3.49, (15, 2): 3.55, (20, 2): 3.78,
    (2, 3): 1.91, (3, 3): 2.24, (4, 3): 2.48, (5, 3): 2.67, (6, 3): 2.83,
    (7, 3): 2.96, (8, 3): 3.08, (9, 3): 3.18, (10, 3): 3.27, (11, 3): 3.35,
    (12, 3): 3.42, (13, 3): 3.49, (14, 3): 3.55, (15, 3): 3.61, (20, 3): 3.83,
}
D2_INFINITE = 3.931

# For m=1, d2* = standard d2 values indexed by g (= n in the d2 table)
_D2_FOR_M1 = {
    1: 1.128, 2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326,
    6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078,
    11: 3.173, 12: 3.258, 13: 3.336, 14: 3.407, 15: 3.472,
    20: 3.735,
}


def get_d2_star(g: int, m: int) -> float:
    """Return d2* with linear interpolation for g not in table."""
    if g >= 20:
        return D2_INFINITE

    # m=1 uses standard d2 table (d2* = d2 when averaging a single range)
    if m == 1:
        if g in _D2_FOR_M1:
            return _D2_FOR_M1[g]
        keys = sorted(_D2_FOR_M1.keys())
        lo_g = max((x for x in keys if x < g), default=keys[0])
        hi_g = min((x for x in keys if x > g), default=keys[-1])
        if lo_g == hi_g:
            return _D2_FOR_M1[lo_g]
        lo_v, hi_v = _D2_FOR_M1[lo_g], _D2_FOR_M1[hi_g]
        return lo_v + (hi_v - lo_v) * (g - lo_g) / (hi_g - lo_g)

    key = (g, m)
    if key in D2_STAR:
        return D2_STAR[key]
    # Find bracketing keys with same m
    candidates = sorted(k[0] for k in D2_STAR if k[1] == m)
    lo_g = max((x for x in candidates if x < g), default=candidates[0])
    hi_g = min((x for x in candidates if x > g), default=candidates[-1])
    if lo_g == hi_g:
        return D2_STAR[(lo_g, m)]
    lo_v = D2_STAR[(lo_g, m)]
    hi_v = D2_STAR[(hi_g, m)]
    return lo_v + (hi_v - lo_v) * (g - lo_g) / (hi_g - lo_g)


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLDS = {
    "grr_acceptable_pct": 10.0,
    "grr_marginal_pct": 30.0,
    "ndc_minimum": 5,
    "study_k": 6,
    "alpha_interaction": 0.25,
}


@dataclass
class GRRResult:
    study_id: str
    method: str
    equipment_id: str
    n_parts: int
    n_operators: int
    n_trials: int
    ev_study: float
    av_study: float
    grr_study: float
    pv_study: float
    tv_study: float
    percent_ev: float
    percent_av: float
    percent_grr: float
    percent_pv: float
    ndc: int
    status: str
    interaction_pooled: bool
    interaction_p_value: float
    anova_table: dict | None
    warnings: list[str]
    recommendations: list[str]
    assumptions: list[str]
    calculation_time_ms: float
    thresholds_used: dict


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate(df: pd.DataFrame) -> tuple[int, int, int]:
    required = {"part_id", "operator_id", "trial", "measurement_value"}
    if missing := required - set(df.columns):
        raise ValueError(f"Missing columns: {missing}")
    if df["measurement_value"].isna().any():
        bad = df[df["measurement_value"].isna()].index.tolist()
        raise ValueError(f"NaN values at rows: {bad}")

    n_parts = df["part_id"].nunique()
    n_operators = df["operator_id"].nunique()
    counts = df.groupby(["part_id", "operator_id"]).size()
    n_trials = int(counts.iloc[0])

    if n_trials < 2:
        raise ValueError(f"Minimum 2 trials required. Got {n_trials}.")
    if n_parts < 2:
        raise ValueError("Minimum 2 parts required.")
    if n_operators < 2:
        raise ValueError("Minimum 2 operators required.")
    return n_parts, n_operators, n_trials


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------
def _classify(
    pct_grr: float,
    ndc: int,
    pct_ev: float,
    pct_av: float,
    interaction_pooled: bool,
    p_interaction: float,
    n_trials: int,
    n_parts: int,
    av_set_zero: bool,
    thresholds: dict,
) -> tuple[str, list[str], list[str]]:
    acc_thr = thresholds.get("grr_acceptable_pct", 10.0)
    marg_thr = thresholds.get("grr_marginal_pct", 30.0)
    ndc_min = thresholds.get("ndc_minimum", 5)

    if pct_grr < acc_thr and ndc >= ndc_min:
        status = "ACCEPTABLE"
    elif pct_grr < marg_thr:
        status = "MARGINAL"
    else:
        status = "NOT_ACCEPTABLE"

    warns: list[str] = []
    if ndc < 5:
        warns.append(f"NDC={ndc}: insufficient discrimination (<5). Consider better gauge.")
    if pct_ev > 0 and pct_av > pct_ev * 2:
        warns.append("Appraiser variation dominates. Review operator training.")
    if not interaction_pooled:
        warns.append(
            f"Significant Part×Operator interaction detected (p={p_interaction:.3f}). "
            "Some operators may measure certain parts differently."
        )
    if n_trials < 3:
        warns.append(
            f"Only {n_trials} trials. Range method precision is reduced. 3+ trials recommended."
        )
    if n_parts < 5:
        warns.append(
            f"Only {n_parts} parts. Insufficient to estimate true part variation. "
            "AIAG recommends 10."
        )
    if av_set_zero:
        warns.append(
            "Reproducibility (AV) set to 0: operator effect not distinguishable from noise."
        )

    recs: list[str]
    match status:
        case "ACCEPTABLE":
            recs = [
                "Measurement system approved. Schedule next calibration per SOP.",
                "Document approval in QMS.",
            ]
        case "MARGINAL":
            max_src = "EV (Repeatability)" if pct_ev >= pct_av else "AV (Reproducibility)"
            recs = [
                f"Investigate primary variation source ({max_src}).",
                "Consider re-study with more parts or operators.",
                "Evaluate acceptability based on application criticality.",
            ]
        case _:
            max_src = "EV (Repeatability)" if pct_ev >= pct_av else "AV (Reproducibility)"
            recs = [
                "Do not use this gauge for production decisions.",
                f"Identify and eliminate dominant variation source ({max_src}).",
                "Re-calibrate equipment and retrain operators before re-study.",
            ]
    return status, warns, recs


# ---------------------------------------------------------------------------
# ANOVA Method
# ---------------------------------------------------------------------------
def run_grr_anova(
    df: pd.DataFrame,
    equipment_id: str,
    thresholds: dict | None = None,
) -> GRRResult:
    t0 = time.perf_counter()
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    n_parts, n_operators, n_trials = _validate(df)
    p, o, r = n_parts, n_operators, n_trials
    k = float(thresholds.get("study_k", 6))
    alpha = float(thresholds.get("alpha_interaction", 0.25))

    parts = sorted(df["part_id"].unique())
    ops = sorted(df["operator_id"].unique())

    grand = float(df["measurement_value"].mean())
    part_means = df.groupby("part_id")["measurement_value"].mean()
    op_means = df.groupby("operator_id")["measurement_value"].mean()
    cell_means = df.groupby(["part_id", "operator_id"])["measurement_value"].mean()

    ss_parts = o * r * float(((part_means - grand) ** 2).sum())
    ss_ops = p * r * float(((op_means - grand) ** 2).sum())

    ss_inter = 0.0
    for pid in parts:
        for oid in ops:
            cm = float(cell_means.loc[(pid, oid)])
            ss_inter += r * (cm - float(part_means[pid]) - float(op_means[oid]) + grand) ** 2

    ss_err = 0.0
    for pid in parts:
        for oid in ops:
            cv = df[(df["part_id"] == pid) & (df["operator_id"] == oid)][
                "measurement_value"
            ].values
            ss_err += float(((cv - cv.mean()) ** 2).sum())

    ss_total = float(((df["measurement_value"] - grand) ** 2).sum())
    assert abs(ss_parts + ss_ops + ss_inter + ss_err - ss_total) < 1e-8, (
        "SS components do not sum to SS_total"
    )

    df_p, df_o = p - 1, o - 1
    df_inter = df_p * df_o
    df_err = p * o * (r - 1)
    df_total = p * o * r - 1

    ms_parts = ss_parts / df_p
    ms_ops = ss_ops / df_o
    ms_inter = ss_inter / df_inter if df_inter > 0 else 0.0
    ms_err = ss_err / df_err if df_err > 0 else 1e-15

    f_inter = ms_inter / ms_err if ms_err > 0 else 0.0
    p_inter = float(f_dist.sf(f_inter, df_inter, df_err))

    interaction_pooled = p_inter > alpha
    av_set_zero = False

    if interaction_pooled:
        ms_ep = (ss_inter + ss_err) / (df_inter + df_err)
        s2_rep = ms_ep
        s2_inter = 0.0
        s2_op = max((ms_ops - ms_ep) / (p * r), 0.0)
        s2_parts = max((ms_parts - ms_ep) / (o * r), 0.0)
        denom_fo = ms_ep
        f_ops = ms_ops / ms_ep if ms_ep > 0 else 0.0
        f_parts = ms_parts / ms_ep if ms_ep > 0 else 0.0
        p_ops = float(f_dist.sf(f_ops, df_o, df_inter + df_err))
        p_parts = float(f_dist.sf(f_parts, df_p, df_inter + df_err))
    else:
        s2_rep = ms_err
        s2_inter = max((ms_inter - ms_err) / r, 0.0)
        s2_op_raw = (ms_ops - ms_inter) / (p * r)
        if s2_op_raw < 0:
            s2_op = 0.0
            av_set_zero = True
        else:
            s2_op = s2_op_raw
        s2_parts = max((ms_parts - ms_inter) / (o * r), 0.0)
        f_ops = ms_ops / ms_inter if ms_inter > 0 else 0.0
        f_parts = ms_parts / ms_inter if ms_inter > 0 else 0.0
        p_ops = float(f_dist.sf(f_ops, df_o, df_inter))
        p_parts = float(f_dist.sf(f_parts, df_p, df_inter))

    s2_grr = s2_rep + s2_op + s2_inter
    s2_total = s2_grr + s2_parts

    ev_study = k * math.sqrt(s2_rep)
    av_study = k * math.sqrt(s2_op + s2_inter)
    grr_study = k * math.sqrt(s2_grr)
    pv_study = k * math.sqrt(s2_parts)
    tv_study = k * math.sqrt(s2_total)

    pct_ev = 100.0 * ev_study / tv_study if tv_study > 0 else 0.0
    pct_av = 100.0 * av_study / tv_study if tv_study > 0 else 0.0
    pct_grr = 100.0 * grr_study / tv_study if tv_study > 0 else 0.0
    pct_pv = 100.0 * pv_study / tv_study if tv_study > 0 else 0.0

    ndc = int(math.floor(1.41 * pv_study / grr_study)) if grr_study > 0 else 0

    status, warns, recs = _classify(
        pct_grr, ndc, pct_ev, pct_av, interaction_pooled, p_inter,
        n_trials, n_parts, av_set_zero, thresholds,
    )

    anova_table = {
        "source": ["Parts", "Operators", "Interaction", "Repeatability", "Total"],
        "SS": [ss_parts, ss_ops, ss_inter, ss_err, ss_total],
        "df": [df_p, df_o, df_inter, df_err, df_total],
        "MS": [ms_parts, ms_ops, ms_inter, ms_err, None],
        "F": [f_parts, f_ops, f_inter, None, None],
        "p_value": [p_parts, p_ops, p_inter, None, None],
    }

    assumptions = [
        "Study variation multiplier k=6 (99.73% coverage). AIAG allows 5.15.",
        "Two-way crossed ANOVA: Y = μ + α_part + β_operator + (αβ)_interaction + ε.",
        f"AIAG alpha threshold for interaction pooling: {alpha} (NOT 0.05).",
        "Variance contributions added in quadrature: %EV² + %AV² ≈ %GRR².",
    ]

    calc_ms = (time.perf_counter() - t0) * 1000

    return GRRResult(
        study_id=str(uuid.uuid4()),
        method="ANOVA",
        equipment_id=equipment_id,
        n_parts=n_parts,
        n_operators=n_operators,
        n_trials=n_trials,
        ev_study=ev_study,
        av_study=av_study,
        grr_study=grr_study,
        pv_study=pv_study,
        tv_study=tv_study,
        percent_ev=pct_ev,
        percent_av=pct_av,
        percent_grr=pct_grr,
        percent_pv=pct_pv,
        ndc=ndc,
        status=status,
        interaction_pooled=interaction_pooled,
        interaction_p_value=p_inter,
        anova_table=anova_table,
        warnings=warns,
        recommendations=recs,
        assumptions=assumptions,
        calculation_time_ms=calc_ms,
        thresholds_used=thresholds,
    )


# ---------------------------------------------------------------------------
# Range Method
# ---------------------------------------------------------------------------
def run_grr_range(
    df: pd.DataFrame,
    equipment_id: str,
    thresholds: dict | None = None,
) -> GRRResult:
    t0 = time.perf_counter()
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS.copy()

    n_parts, n_operators, n_trials = _validate(df)
    p, o, r = n_parts, n_operators, n_trials
    k = float(thresholds.get("study_k", 6))

    # Step 1 — EV
    cell_ranges = []
    for pid in df["part_id"].unique():
        for oid in df["operator_id"].unique():
            cv = df[(df["part_id"] == pid) & (df["operator_id"] == oid)][
                "measurement_value"
            ].values
            cell_ranges.append(float(np.ptp(cv)))
    r_bar = float(np.mean(cell_ranges))
    g_ev = p * o
    ev = r_bar / get_d2_star(g_ev, r)

    # Step 2 — AV
    op_grand_means = {
        oid: float(df[df["operator_id"] == oid]["measurement_value"].mean())
        for oid in df["operator_id"].unique()
    }
    x_diff = max(op_grand_means.values()) - min(op_grand_means.values())
    d2_av = get_d2_star(o, 1)
    x_bar_sigma = x_diff / d2_av

    av_raw_sq = x_bar_sigma ** 2 - (ev ** 2 / (p * r))
    av_set_zero = av_raw_sq < 0
    if av_set_zero:
        warnings.warn("AV set to 0 — operator effect dominated by repeatability noise")
        av = 0.0
    else:
        av = math.sqrt(av_raw_sq)

    # Step 3-5
    grr = math.sqrt(ev ** 2 + av ** 2)

    part_means_arr = np.array([
        float(df[df["part_id"] == pid]["measurement_value"].mean())
        for pid in df["part_id"].unique()
    ])
    r_p = float(np.ptp(part_means_arr))
    pv = r_p / get_d2_star(p, 1)

    tv = math.sqrt(grr ** 2 + pv ** 2)

    # Step 6-7
    ev_study = k * ev
    av_study = k * av
    grr_study = k * grr
    pv_study = k * pv
    tv_study = k * tv

    pct_ev = 100.0 * ev_study / tv_study if tv_study > 0 else 0.0
    pct_av = 100.0 * av_study / tv_study if tv_study > 0 else 0.0
    pct_grr = 100.0 * grr_study / tv_study if tv_study > 0 else 0.0
    pct_pv = 100.0 * pv_study / tv_study if tv_study > 0 else 0.0

    ndc = int(math.floor(1.41 * pv_study / grr_study)) if grr_study > 0 else 0

    status, warns, recs = _classify(
        pct_grr, ndc, pct_ev, pct_av, True, 1.0,
        n_trials, n_parts, av_set_zero, thresholds,
    )
    if n_trials < 3:
        if f"Only {n_trials} trials." not in " ".join(warns):
            warns.append(
                f"Only {n_trials} trials. Range method precision is reduced. 3+ trials recommended."
            )

    assumptions = [
        "Study variation multiplier k=6 (99.73% coverage). AIAG allows 5.15.",
        "Range method per AIAG MSA 4th Ed with d2* lookup (Table D3).",
        "Linear interpolation used for g values not in d2* table.",
        "AV = max(0, sqrt(x_bar_sigma² - EV²/(n_parts×n_trials))) per AIAG.",
    ]

    calc_ms = (time.perf_counter() - t0) * 1000

    return GRRResult(
        study_id=str(uuid.uuid4()),
        method="Range",
        equipment_id=equipment_id,
        n_parts=n_parts,
        n_operators=n_operators,
        n_trials=n_trials,
        ev_study=ev_study,
        av_study=av_study,
        grr_study=grr_study,
        pv_study=pv_study,
        tv_study=tv_study,
        percent_ev=pct_ev,
        percent_av=pct_av,
        percent_grr=pct_grr,
        percent_pv=pct_pv,
        ndc=ndc,
        status=status,
        interaction_pooled=True,
        interaction_p_value=1.0,
        anova_table=None,
        warnings=warns,
        recommendations=recs,
        assumptions=assumptions,
        calculation_time_ms=calc_ms,
        thresholds_used=thresholds,
    )
