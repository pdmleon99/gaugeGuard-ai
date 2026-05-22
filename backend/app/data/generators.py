"""Sample data generators for GaugeGuard AI — reproducible with seed=42."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(seed=42)

def _resolve_samples_dir() -> Path:
    import os
    env = os.getenv("GAUGEDATA_DIR")
    if env:
        return Path(env) / "samples"
    # Local dev: walk up to gaugeGuard project root
    return Path(__file__).parent.parent.parent.parent / "data" / "samples"

SAMPLES_DIR = _resolve_samples_dir()


def _anova_grr(df: pd.DataFrame) -> float:
    """Quick ANOVA %GRR for generator validation."""
    parts = df["part_id"].unique()
    ops = df["operator_id"].unique()
    p, o = len(parts), len(ops)
    r = df.groupby(["part_id", "operator_id"]).size().iloc[0]

    grand = df["measurement_value"].mean()
    part_means = df.groupby("part_id")["measurement_value"].mean()
    op_means = df.groupby("operator_id")["measurement_value"].mean()

    cell_means = df.groupby(["part_id", "operator_id"])["measurement_value"].mean()

    ss_parts = o * r * ((part_means - grand) ** 2).sum()
    ss_ops = p * r * ((op_means - grand) ** 2).sum()

    ss_inter = 0.0
    for pid in parts:
        for oid in ops:
            cm = cell_means.loc[(pid, oid)]
            ss_inter += r * (cm - part_means[pid] - op_means[oid] + grand) ** 2

    vals = df["measurement_value"].values
    ss_err = 0.0
    for pid in parts:
        for oid in ops:
            cell_vals = df[(df["part_id"] == pid) & (df["operator_id"] == oid)][
                "measurement_value"
            ].values
            cm = cell_vals.mean()
            ss_err += ((cell_vals - cm) ** 2).sum()

    df_p = p - 1
    df_o = o - 1
    df_inter = df_p * df_o
    df_err = p * o * (r - 1)

    ms_inter = ss_inter / df_inter if df_inter > 0 else 0
    ms_err = ss_err / df_err if df_err > 0 else 1e-12
    ms_ops = ss_ops / df_o if df_o > 0 else 0
    ms_parts = ss_parts / df_p if df_p > 0 else 0

    from scipy.stats import f as f_dist

    f_inter = ms_inter / ms_err
    p_inter = f_dist.sf(f_inter, df_inter, df_err)

    alpha = 0.25
    if p_inter > alpha:
        ms_ep = (ss_inter + ss_err) / (df_inter + df_err)
        s2_rep = ms_ep
        s2_op = max((ms_ops - ms_ep) / (p * r), 0.0)
        s2_parts = max((ms_parts - ms_ep) / (o * r), 0.0)
        s2_inter = 0.0
    else:
        s2_rep = ms_err
        s2_inter = max((ms_inter - ms_err) / r, 0.0)
        s2_op = max((ms_ops - ms_inter) / (p * r), 0.0)
        s2_parts = max((ms_parts - ms_inter) / (o * r), 0.0)

    s2_grr = s2_rep + s2_op + s2_inter
    s2_total = s2_grr + s2_parts

    if s2_total < 1e-15:
        return 0.0
    return 100.0 * math.sqrt(s2_grr / s2_total)


def _make_grr_df(
    part_sigma: float,
    noise_sigma: float,
    op_bias: list[float],
    rng: np.random.Generator,
) -> pd.DataFrame:
    parts = [f"P{i:02d}" for i in range(1, 11)]
    operators = ["OP1", "OP2", "OP3"]
    op_names = {"OP1": "Alice", "OP2": "Bob", "OP3": "Carlos"}
    nominal = 25.0
    usl, lsl = 25.5, 24.5

    part_values = {p: nominal + rng.normal(0, part_sigma) for p in parts}

    rows = []
    ts = pd.Timestamp("2024-01-15 08:00:00")
    for trial in range(1, 4):
        for op_idx, op in enumerate(operators):
            for part in parts:
                val = part_values[part] + op_bias[op_idx] + rng.normal(0, noise_sigma)
                rows.append(
                    {
                        "part_id": part,
                        "operator_id": op,
                        "operator_name": op_names[op],
                        "trial": trial,
                        "measurement_value": round(val, 6),
                        "nominal_value": nominal,
                        "USL": usl,
                        "LSL": lsl,
                        "unit": "mm",
                        "equipment_id": "CMM-001",
                        "timestamp": ts.isoformat(),
                        "batch_id": "BATCH-2024-001",
                    }
                )
                ts += pd.Timedelta(minutes=5)
    return pd.DataFrame(rows)


def generate_grr_samples() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed=42)

    configs = {
        "grr_pass": {
            "part_sigma": 0.15,
            "noise_sigma": 0.011,
            "op_bias": [0.0, 0.002, -0.002],
            "target_lo": 5.0,
            "target_hi": 9.0,
        },
        "grr_marginal": {
            "part_sigma": 0.15,
            "noise_sigma": 0.035,
            "op_bias": [0.0, 0.025, -0.018],
            "target_lo": 15.0,
            "target_hi": 25.0,
        },
        "grr_fail": {
            "part_sigma": 0.15,
            "noise_sigma": 0.060,
            "op_bias": [0.0, 0.045, -0.040],
            "target_lo": 35.0,
            "target_hi": 50.0,
        },
    }

    for name, cfg in configs.items():
        local_rng = np.random.default_rng(seed=42)
        df = _make_grr_df(
            cfg["part_sigma"], cfg["noise_sigma"], cfg["op_bias"], local_rng
        )
        pct = _anova_grr(df)
        print(f"  {name}: %GRR = {pct:.2f}% (target {cfg['target_lo']}–{cfg['target_hi']}%)")
        assert cfg["target_lo"] <= pct <= cfg["target_hi"], (
            f"{name} %GRR={pct:.2f}% outside [{cfg['target_lo']},{cfg['target_hi']}]"
        )
        out = SAMPLES_DIR / f"{name}.csv"
        df.to_csv(out, index=False)
        print(f"  Saved {out}")


def generate_spc_samples() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    N = 200
    base_ts = pd.Timestamp("2024-01-15 06:00:00")

    def make_base_row(i: int, val: float, process_id: str) -> dict:
        return {
            "timestamp": (base_ts + pd.Timedelta(minutes=3 * i)).isoformat(),
            "measurement_value": round(val, 6),
            "subgroup_id": i // 5,
            "process_id": process_id,
            "equipment_id": "CNC-001",
            "metric": "diameter_mm",
            "nominal": 25.0,
            "USL": 25.3,
            "LSL": 24.7,
        }

    # --- spc_stable ---
    rng = np.random.default_rng(seed=42)
    rows = [make_base_row(i, 25.0 + rng.normal(0, 0.05), "LINE-A") for i in range(N)]
    df_stable = pd.DataFrame(rows)
    df_stable.to_csv(SAMPLES_DIR / "spc_stable.csv", index=False)
    print("  spc_stable.csv: generated 200 rows (mu=25.0, sigma=0.05)")

    # --- spc_shift ---
    rng = np.random.default_rng(seed=42)
    vals = []
    for i in range(N):
        mu = 25.0 if i < 100 else 25.18
        vals.append(25.0 + (mu - 25.0) + rng.normal(0, 0.05))
    rows = [make_base_row(i, vals[i], "LINE-A") for i in range(N)]
    df_shift = pd.DataFrame(rows)
    df_shift.to_csv(SAMPLES_DIR / "spc_shift.csv", index=False)
    print("  spc_shift.csv: shift of +0.18 (3.6σ) at point 100")

    # --- spc_drift ---
    rng = np.random.default_rng(seed=42)
    vals = [25.0 + 0.003 * i + rng.normal(0, 0.04) for i in range(N)]
    rows = [make_base_row(i, vals[i], "LINE-A") for i in range(N)]
    df_drift = pd.DataFrame(rows)
    df_drift.to_csv(SAMPLES_DIR / "spc_drift.csv", index=False)
    print("  spc_drift.csv: drift +0.003/point, sigma=0.04")

    # --- spc_anomalies ---
    rng = np.random.default_rng(seed=42)
    vals = [25.0 + rng.normal(0, 0.05) for _ in range(N)]
    outlier_indices = [40, 80, 120, 160, 195]
    for idx in outlier_indices:
        vals[idx] = 25.0 + 0.25  # +5σ spike
    rows = [make_base_row(i, vals[i], "LINE-A") for i in range(N)]
    df_anom = pd.DataFrame(rows)
    df_anom.to_csv(SAMPLES_DIR / "spc_anomalies.csv", index=False)
    print(f"  spc_anomalies.csv: outliers at indices {outlier_indices}")

    # Validate spc outputs with a quick Nelson Rule 1 check
    _validate_spc_samples(df_stable, df_shift, df_drift, df_anom)


def _nelson_rule1_quick(values: list[float], cl: float, sigma: float) -> list[int]:
    return [i for i, v in enumerate(values) if abs(v - cl) > 3 * sigma]


def _nelson_rule2_quick(values: list[float], cl: float) -> list[int]:
    violations = []
    for start in range(len(values) - 8):
        window = values[start : start + 9]
        if all(v > cl for v in window) or all(v < cl for v in window):
            violations.append(start + 8)
    return violations


def _nelson_rule3_quick(values: list[float]) -> list[int]:
    violations = []
    for start in range(len(values) - 5):
        window = values[start : start + 6]
        if all(window[i] < window[i + 1] for i in range(5)) or all(
            window[i] > window[i + 1] for i in range(5)
        ):
            violations.append(start + 5)
    return violations


def _validate_spc_samples(
    df_stable: pd.DataFrame,
    df_shift: pd.DataFrame,
    df_drift: pd.DataFrame,
    df_anom: pd.DataFrame,
) -> None:
    # Validate stable (subgroup_size=5 → use subgroup means)
    def subgroup_means(df: pd.DataFrame) -> list[float]:
        return [
            df[df["subgroup_id"] == g]["measurement_value"].mean()
            for g in sorted(df["subgroup_id"].unique())
        ]

    stable_means = subgroup_means(df_stable)
    cl = float(np.mean(stable_means))
    from scipy.stats import tstd
    ranges = []
    for g in sorted(df_stable["subgroup_id"].unique()):
        sub = df_stable[df_stable["subgroup_id"] == g]["measurement_value"].values
        ranges.append(float(np.ptp(sub)))
    r_bar = float(np.mean(ranges))
    d2_5 = 2.326
    sigma = r_bar / d2_5
    r1 = _nelson_rule1_quick(stable_means, cl, sigma)
    print(f"  spc_stable validation: Rule 1 violations = {len(r1)} (expect 0)")

    # Validate shift
    shift_vals = df_shift["measurement_value"].tolist()
    cl2 = float(np.mean(shift_vals[:100]))
    rng_vals = [abs(shift_vals[i] - shift_vals[i - 1]) for i in range(1, 101)]
    mr_bar = float(np.mean(rng_vals))
    sigma2 = mr_bar / 1.128
    r2_run = _nelson_rule2_quick(shift_vals, cl2)
    r1_shift = _nelson_rule1_quick(shift_vals, cl2, sigma2)
    print(f"  spc_shift validation: Rule 1={len(r1_shift)}, Rule 2 runs={len(r2_run)} (need >0)")

    # Validate drift
    drift_vals = df_drift["measurement_value"].tolist()
    cl3 = float(np.mean(drift_vals[:25]))
    rng3 = [abs(drift_vals[i] - drift_vals[i - 1]) for i in range(1, 26)]
    sigma3 = float(np.mean(rng3)) / 1.128
    r3 = _nelson_rule3_quick(drift_vals)
    r1_drift = _nelson_rule1_quick(drift_vals, cl3, sigma3)
    print(f"  spc_drift validation: Rule 3 trends={len(r3)}, Rule 1={len(r1_drift)} (need Rule 3 > 0)")

    # Validate anomalies
    anom_vals = df_anom["measurement_value"].tolist()
    cl4 = 25.0
    rng4 = [abs(anom_vals[i] - anom_vals[i - 1]) for i in range(1, 200)]
    sigma4 = float(np.mean(rng4)) / 1.128
    r1_anom = _nelson_rule1_quick(anom_vals, cl4, sigma4)
    print(f"  spc_anomalies validation: Rule 1 violations = {len(r1_anom)} at {r1_anom} (expect indices near {[40,80,120,160,195]})")


if __name__ == "__main__":
    print("=== Generating GR&R samples ===")
    generate_grr_samples()
    print("\n=== Generating SPC samples ===")
    generate_spc_samples()
    print("\n=== All samples generated successfully ===")
