"""SPC Engine — Nelson Rules, control limits, X-bar/R/I-MR charts."""
from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# SPC Constants (AIAG exact values)
# ---------------------------------------------------------------------------
SPC_CONSTANTS: dict[str, dict] = {
    "A2":  {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308},
    "D3":  {2: 0,     3: 0,     4: 0,     5: 0,     6: 0,     7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223},
    "D4":  {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777},
    "d2":  {1: 1.128, 2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326, 6: 2.534, 7: 2.704, 8: 2.847, 9: 2.970, 10: 3.078},
    "A3":  {2: 2.659, 3: 1.954, 4: 1.628, 5: 1.427, 6: 1.287, 7: 1.182, 8: 1.099, 9: 1.032, 10: 0.975},
    "B3":  {2: 0,     3: 0,     4: 0,     5: 0,     6: 0.030, 7: 0.118, 8: 0.185, 9: 0.239, 10: 0.284},
    "B4":  {2: 3.267, 3: 2.568, 4: 2.266, 5: 2.089, 6: 1.970, 7: 1.882, 8: 1.815, 9: 1.761, 10: 1.716},
    "E2":  2.66,
}

DEFAULT_RULES = {f"rule_{i}": True for i in range(1, 9)}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
@dataclass
class SPCViolation:
    alert_id: str
    timestamp: datetime
    process_id: str
    equipment_id: str
    metric: str
    rule_triggered: str
    severity: str
    point_index: int
    observed_value: float
    cl_center: float
    ucl: float
    lcl: float
    sigma_hat: float
    explanation: str
    recommended_action: str
    confidence_score: float = 1.0
    false_positive_feedback: str | None = None


@dataclass
class SPCResult:
    analysis_id: str
    process_id: str
    chart_type: str
    n_subgroups: int
    subgroup_size: int
    baseline_n: int
    x_bar_bar: float
    r_bar: float
    sigma_hat: float
    ucl_x: float
    lcl_x: float
    ucl_r: float
    lcl_r: float
    violations: list[SPCViolation]
    n_critical: int
    n_warning: int
    n_info: int
    process_status: str
    chart_data: list[dict]


# ---------------------------------------------------------------------------
# Nelson Rule Checks
# ---------------------------------------------------------------------------
_RULE_ACTIONS = {
    "Rule 1": "Immediately investigate. Likely special cause: tool failure, setup error, or measurement error.",
    "Rule 2": "Investigate process mean shift. Check recent setups, raw material batches, operator changes.",
    "Rule 3": "Investigate process drift. Check tool wear, temperature effects, operator fatigue.",
    "Rule 4": "Review measurement system or sampling. May indicate mixed-stream sampling.",
    "Rule 5": "Early shift warning. Investigate recent process changes before situation escalates.",
    "Rule 6": "Subtle shift detected. Review process parameters and inputs.",
    "Rule 7": "Investigate stratified sampling or over-correction by operators.",
    "Rule 8": "Bimodal distribution suspected. Check for two distinct process streams.",
    "SPEC_VIOLATION": "Immediate stop and quarantine affected product. Notify quality engineer.",
}


def _make_violation(
    rule: str,
    severity: str,
    idx: int,
    val: float,
    cl: float,
    ucl: float,
    lcl: float,
    sigma_hat: float,
    explanation: str,
    process_id: str,
    equipment_id: str,
    metric: str,
    ts: datetime,
) -> SPCViolation:
    return SPCViolation(
        alert_id=str(uuid.uuid4()),
        timestamp=ts,
        process_id=process_id,
        equipment_id=equipment_id,
        metric=metric,
        rule_triggered=rule,
        severity=severity,
        point_index=idx,
        observed_value=val,
        cl_center=cl,
        ucl=ucl,
        lcl=lcl,
        sigma_hat=sigma_hat,
        explanation=explanation,
        recommended_action=_RULE_ACTIONS.get(rule, "Investigate."),
    )


def check_nelson_rules(
    values: list[float],
    cl: float,
    sigma_hat: float,
    ucl: float,
    lcl: float,
    enabled_rules: dict[str, bool],
    process_id: str,
    equipment_id: str,
    metric: str,
    timestamps: list[datetime],
) -> list[SPCViolation]:
    violations: list[SPCViolation] = []
    n = len(values)

    def ts(i: int) -> datetime:
        return timestamps[i] if i < len(timestamps) else datetime.utcnow()

    # Rule 1 — beyond 3σ
    if enabled_rules.get("rule_1", True):
        for i, v in enumerate(values):
            if abs(v - cl) > 3 * sigma_hat:
                side = "above" if v > cl else "below"
                exp = (
                    f"Rule 1: Point {i} ({v:.4f}) is {side} 3σ control limit "
                    f"(UCL={ucl:.4f}/LCL={lcl:.4f}). Indicates special cause variation."
                )
                violations.append(_make_violation(
                    "Rule 1", "critical", i, v, cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(i)
                ))

    # Rule 2 — 9 consecutive same side
    if enabled_rules.get("rule_2", True):
        reported_ends: set[int] = set()
        for start in range(n - 8):
            window = values[start: start + 9]
            end = start + 8
            if end in reported_ends:
                continue
            if all(v > cl for v in window) or all(v < cl for v in window):
                exp = (
                    f"Rule 2: Points {start}–{end} all on same side of centerline "
                    f"(CL={cl:.4f}). Indicates process mean shift."
                )
                violations.append(_make_violation(
                    "Rule 2", "warning", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))
                reported_ends.add(end)

    # Rule 3 — 6 consecutive monotone
    if enabled_rules.get("rule_3", True):
        reported_ends3: set[int] = set()
        for start in range(n - 5):
            w = values[start: start + 6]
            end = start + 5
            if end in reported_ends3:
                continue
            if all(w[i] < w[i + 1] for i in range(5)) or all(w[i] > w[i + 1] for i in range(5)):
                direction = "increasing" if w[-1] > w[0] else "decreasing"
                exp = (
                    f"Rule 3: Points {start}–{end} show consistent {direction} trend. "
                    "Indicates process drift."
                )
                violations.append(_make_violation(
                    "Rule 3", "warning", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))
                reported_ends3.add(end)

    # Rule 4 — 14 alternating points
    if enabled_rules.get("rule_4", True) and n >= 14:
        for start in range(n - 13):
            w = values[start: start + 14]
            end = start + 13
            alternating = all(
                math.copysign(1, w[i + 1] - w[i]) != math.copysign(1, w[i] - w[i - 1])
                for i in range(1, 13)
            )
            if alternating:
                exp = (
                    f"Rule 4: Points {start}–{end} show 14-point alternating pattern. "
                    "May indicate measurement system issues or sampling from mixed streams."
                )
                violations.append(_make_violation(
                    "Rule 4", "info", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))
                break  # only report once per window start

    # Rule 5 — 2 of 3 beyond 2σ same side
    if enabled_rules.get("rule_5", True):
        for start in range(n - 2):
            w = values[start: start + 3]
            end = start + 2
            above = sum(1 for v in w if v > cl + 2 * sigma_hat)
            below = sum(1 for v in w if v < cl - 2 * sigma_hat)
            if above >= 2 or below >= 2:
                exp = (
                    f"Rule 5: 2 of 3 consecutive points (ending at {end}) beyond 2σ. "
                    "Early shift indicator."
                )
                violations.append(_make_violation(
                    "Rule 5", "warning", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))

    # Rule 6 — 4 of 5 beyond 1σ same side
    if enabled_rules.get("rule_6", True):
        for start in range(n - 4):
            w = values[start: start + 5]
            end = start + 4
            above = sum(1 for v in w if v > cl + sigma_hat)
            below = sum(1 for v in w if v < cl - sigma_hat)
            if above >= 4 or below >= 4:
                exp = (
                    f"Rule 6: 4 of 5 consecutive points (ending at {end}) beyond 1σ. "
                    "Subtle shift or increased variation."
                )
                violations.append(_make_violation(
                    "Rule 6", "info", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))

    # Rule 7 — 15 consecutive within 1σ
    if enabled_rules.get("rule_7", True) and n >= 15:
        for start in range(n - 14):
            w = values[start: start + 15]
            end = start + 14
            if all(abs(v - cl) < sigma_hat for v in w):
                exp = (
                    f"Rule 7: Points {start}–{end} all within 1σ of centerline. "
                    "May indicate stratified sampling or over-control."
                )
                violations.append(_make_violation(
                    "Rule 7", "info", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))
                break

    # Rule 8 — 8 consecutive beyond 1σ (both sides)
    if enabled_rules.get("rule_8", True) and n >= 8:
        for start in range(n - 7):
            w = values[start: start + 8]
            end = start + 7
            if all(abs(v - cl) > sigma_hat for v in w):
                exp = (
                    f"Rule 8: Points {start}–{end} all beyond 1σ from centerline. "
                    "Bimodal process suspected."
                )
                violations.append(_make_violation(
                    "Rule 8", "warning", end, values[end], cl, ucl, lcl, sigma_hat, exp,
                    process_id, equipment_id, metric, ts(end)
                ))
                break

    return violations


# ---------------------------------------------------------------------------
# Main SPC Analysis
# ---------------------------------------------------------------------------
def run_spc_analysis(
    df: pd.DataFrame,
    process_id: str,
    subgroup_size: int = 5,
    baseline_n: int = 25,
    enabled_rules: dict[str, bool] | None = None,
    usl: float | None = None,
    lsl: float | None = None,
) -> SPCResult:
    if enabled_rules is None:
        enabled_rules = DEFAULT_RULES.copy()

    equipment_id = str(df.get("equipment_id", pd.Series(["UNKNOWN"])).iloc[0]) if "equipment_id" in df.columns else "UNKNOWN"
    metric = str(df.get("metric", pd.Series(["measurement"])).iloc[0]) if "metric" in df.columns else "measurement"

    if "USL" in df.columns and usl is None:
        usl = float(df["USL"].iloc[0])
    if "LSL" in df.columns and lsl is None:
        lsl = float(df["LSL"].iloc[0])

    if "timestamp" in df.columns:
        timestamps = [
            pd.to_datetime(t).to_pydatetime() if not isinstance(t, datetime) else t
            for t in df["timestamp"].tolist()
        ]
    else:
        base = datetime.utcnow()
        timestamps = [base + timedelta(minutes=3 * i) for i in range(len(df))]

    vals = df["measurement_value"].tolist()
    n = len(vals)
    actual_baseline = min(baseline_n, n)
    if actual_baseline < 10:
        import warnings
        warnings.warn(f"Less than 10 subgroups. Control limits unreliable (n={actual_baseline}).")

    n = subgroup_size  # rename for chart constants
    chart_type: str
    if subgroup_size == 1:
        chart_type = "IMR"
    elif subgroup_size <= 8:
        chart_type = "XbarR"
    else:
        chart_type = "XbarS"

    all_vals = df["measurement_value"].values
    total_pts = len(all_vals)

    if chart_type in ("XbarR", "XbarS"):
        # Build subgroups
        subgroups = []
        sg_col = df.get("subgroup_id", None)
        if sg_col is not None and "subgroup_id" in df.columns:
            for gid in sorted(df["subgroup_id"].unique()):
                grp = df[df["subgroup_id"] == gid]["measurement_value"].values
                subgroups.append(grp)
        else:
            for i in range(0, total_pts - subgroup_size + 1, subgroup_size):
                subgroups.append(all_vals[i: i + subgroup_size])

        sg_means = np.array([float(np.mean(sg)) for sg in subgroups])
        sg_ranges = np.array([float(np.ptp(sg)) for sg in subgroups])
        n_sub = len(subgroups)
        bl = min(actual_baseline, n_sub)

        x_bar_bar = float(np.mean(sg_means[:bl]))
        r_bar = float(np.mean(sg_ranges[:bl]))
        d2_val = SPC_CONSTANTS["d2"].get(subgroup_size, SPC_CONSTANTS["d2"][10])
        sigma_hat = r_bar / d2_val

        a2 = SPC_CONSTANTS["A2"].get(subgroup_size, SPC_CONSTANTS["A2"][10])
        d3 = SPC_CONSTANTS["D3"].get(subgroup_size, SPC_CONSTANTS["D3"][10])
        d4 = SPC_CONSTANTS["D4"].get(subgroup_size, SPC_CONSTANTS["D4"][10])

        ucl_x = x_bar_bar + a2 * r_bar
        lcl_x = x_bar_bar - a2 * r_bar
        ucl_r = d4 * r_bar
        lcl_r = d3 * r_bar

        # Chart data uses subgroup means for Nelson checks
        chart_values = sg_means.tolist()
        chart_ts = [
            timestamps[min(i * subgroup_size, len(timestamps) - 1)]
            for i in range(n_sub)
        ]
        chart_data = [
            {
                "index": i,
                "value": float(sg_means[i]),
                "subgroup_mean": float(sg_means[i]),
                "subgroup_range": float(sg_ranges[i]),
            }
            for i in range(n_sub)
        ]

    else:  # IMR
        individuals = all_vals
        moving_ranges = np.abs(np.diff(individuals))
        bl = min(actual_baseline, len(individuals))

        x_bar = float(np.mean(individuals[:bl]))
        mr_bar = float(np.mean(moving_ranges[: bl - 1])) if bl > 1 else 0.0
        sigma_hat = mr_bar / 1.128  # d2[2]

        e2 = SPC_CONSTANTS["E2"]
        ucl_x = x_bar + e2 * mr_bar
        lcl_x = x_bar - e2 * mr_bar
        ucl_r = SPC_CONSTANTS["D4"][2] * mr_bar
        lcl_r = 0.0
        x_bar_bar = x_bar
        r_bar = mr_bar

        chart_values = individuals.tolist()
        chart_ts = timestamps
        chart_data = [
            {
                "index": i,
                "value": float(individuals[i]),
                "subgroup_mean": float(individuals[i]),
                "subgroup_range": float(moving_ranges[i - 1]) if i > 0 else 0.0,
            }
            for i in range(len(individuals))
        ]

    violations = check_nelson_rules(
        chart_values, x_bar_bar, sigma_hat, ucl_x, lcl_x,
        enabled_rules, process_id, equipment_id, metric, chart_ts,
    )

    # Spec limit violations
    if usl is not None or lsl is not None:
        for i, v in enumerate(chart_values):
            if (usl is not None and v > usl) or (lsl is not None and v < lsl):
                side = "above USL" if (usl and v > usl) else "below LSL"
                limit = usl if (usl and v > usl) else lsl
                exp = f"SPEC_VIOLATION: Point {i} ({v:.4f}) {side} ({limit:.4f})."
                violations.append(_make_violation(
                    "SPEC_VIOLATION", "critical", i, v, x_bar_bar, ucl_x, lcl_x,
                    sigma_hat, exp, process_id, equipment_id, metric, chart_ts[i]
                ))

    n_critical = sum(1 for v in violations if v.severity == "critical")
    n_warning = sum(1 for v in violations if v.severity == "warning")
    n_info = sum(1 for v in violations if v.severity == "info")

    if n_critical > 0:
        process_status = "OUT_OF_CONTROL"
    elif n_warning > 0:
        process_status = "WARNING"
    else:
        process_status = "IN_CONTROL"

    return SPCResult(
        analysis_id=str(uuid.uuid4()),
        process_id=process_id,
        chart_type=chart_type,
        n_subgroups=len(chart_values),
        subgroup_size=subgroup_size,
        baseline_n=bl,
        x_bar_bar=x_bar_bar,
        r_bar=r_bar,
        sigma_hat=sigma_hat,
        ucl_x=ucl_x,
        lcl_x=lcl_x,
        ucl_r=ucl_r,
        lcl_r=lcl_r,
        violations=violations,
        n_critical=n_critical,
        n_warning=n_warning,
        n_info=n_info,
        process_status=process_status,
        chart_data=chart_data,
    )
