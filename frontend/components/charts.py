"""Plotly chart builders for GaugeGuard AI."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def grr_pie_chart(percent_ev: float, percent_av: float, percent_pv: float) -> go.Figure:
    labels = ["EV (Repeatability)", "AV (Reproducibility)", "PV (Part Variation)"]
    values = [percent_ev ** 2, percent_av ** 2, percent_pv ** 2]
    colors = ["#e74c3c", "#f39c12", "#27ae60"]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.4,
        marker_colors=colors,
        textinfo="label+percent",
    ))
    fig.update_layout(title="Variance Contribution (squared %)", showlegend=True, height=350)
    return fig


def spc_chart(
    chart_data: list[dict],
    ucl_x: float,
    lcl_x: float,
    cl_x: float,
    ucl_r: float,
    lcl_r: float,
    cl_r: float,
    violations: list[dict],
    title: str = "SPC Control Chart",
) -> go.Figure:
    indices = [d["index"] for d in chart_data]
    means = [d["subgroup_mean"] for d in chart_data]
    ranges = [d["subgroup_range"] for d in chart_data]

    critical_idx = [v["point_index"] for v in violations if v["severity"] == "critical"]
    warning_idx = [v["point_index"] for v in violations if v["severity"] == "warning"]

    fig = make_subplots(rows=2, cols=1, subplot_titles=("X-bar Chart", "R Chart"), vertical_spacing=0.12)

    # X-bar
    fig.add_trace(go.Scatter(x=indices, y=means, mode="lines+markers", name="X̄",
                             line=dict(color="#2980b9")), row=1, col=1)
    for lbl, val, color, dash in [
        ("UCL", ucl_x, "red", "dash"),
        ("CL", cl_x, "green", "dot"),
        ("LCL", lcl_x, "red", "dash"),
    ]:
        fig.add_hline(y=val, line=dict(color=color, dash=dash, width=1.5),
                      annotation_text=f"{lbl}={val:.4f}", annotation_position="right",
                      row=1, col=1)

    # Mark violations
    if critical_idx:
        crit_vals = [means[i] for i in critical_idx if i < len(means)]
        fig.add_trace(go.Scatter(x=critical_idx, y=crit_vals, mode="markers",
                                 marker=dict(symbol="x", size=12, color="red"),
                                 name="Critical"), row=1, col=1)
    if warning_idx:
        warn_vals = [means[i] for i in warning_idx if i < len(means)]
        fig.add_trace(go.Scatter(x=warning_idx, y=warn_vals, mode="markers",
                                 marker=dict(symbol="triangle-up", size=10, color="orange"),
                                 name="Warning"), row=1, col=1)

    # R chart
    fig.add_trace(go.Scatter(x=indices, y=ranges, mode="lines+markers", name="R",
                             line=dict(color="#8e44ad")), row=2, col=1)
    fig.add_hline(y=ucl_r, line=dict(color="red", dash="dash", width=1.5),
                  annotation_text=f"UCL_R={ucl_r:.4f}", row=2, col=1)
    fig.add_hline(y=cl_r, line=dict(color="green", dash="dot", width=1.5),
                  annotation_text=f"R̄={cl_r:.4f}", row=2, col=1)

    fig.update_layout(title=title, height=600, showlegend=True)
    return fig
