"""Anomaly engine — wraps SPC violations with process-level scoring."""
from __future__ import annotations

from .spc_engine import SPCResult, SPCViolation


def score_anomaly(violation: SPCViolation) -> float:
    """Return 0-1 anomaly score from a deterministic SPC violation."""
    match violation.severity:
        case "critical":
            return 1.0
        case "warning":
            return 0.7
        case "info":
            return 0.4
        case _:
            return 0.5


def summarize_anomalies(result: SPCResult) -> dict:
    return {
        "analysis_id": result.analysis_id,
        "process_status": result.process_status,
        "n_critical": result.n_critical,
        "n_warning": result.n_warning,
        "n_info": result.n_info,
        "total_violations": len(result.violations),
        "dominant_rule": _dominant_rule(result.violations),
    }


def _dominant_rule(violations: list[SPCViolation]) -> str | None:
    if not violations:
        return None
    counts: dict[str, int] = {}
    for v in violations:
        counts[v.rule_triggered] = counts.get(v.rule_triggered, 0) + 1
    return max(counts, key=lambda k: counts[k])
