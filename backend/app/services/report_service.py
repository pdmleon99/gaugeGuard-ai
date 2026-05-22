"""HTML report generator for GR&R studies."""
from __future__ import annotations

from datetime import datetime

from ..engines.grr_engine import GRRResult


def generate_grr_html_report(result: GRRResult, dataset_name: str = "") -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    status_color = {"ACCEPTABLE": "#27ae60", "MARGINAL": "#f39c12", "NOT_ACCEPTABLE": "#e74c3c"}.get(
        result.status, "#7f8c8d"
    )

    max_src = "EV (Repeatability)" if result.percent_ev >= result.percent_av else "AV (Reproducibility)"

    match result.status:
        case "ACCEPTABLE":
            thr = result.thresholds_used.get("grr_acceptable_pct", 10.0)
            summary = (
                f"The measurement system for equipment <strong>{result.equipment_id}</strong> "
                f"achieved a %GRR of <strong>{result.percent_grr:.1f}%</strong>, "
                f"below the {thr}% acceptance threshold. With {result.ndc} distinct categories, "
                f"the gauge demonstrates adequate discrimination for production use."
            )
        case "MARGINAL":
            lo = result.thresholds_used.get("grr_acceptable_pct", 10.0)
            hi = result.thresholds_used.get("grr_marginal_pct", 30.0)
            summary = (
                f"The measurement system for <strong>{result.equipment_id}</strong> returned "
                f"a %GRR of <strong>{result.percent_grr:.1f}%</strong>, in the marginal range "
                f"({lo}–{hi}%). Suitability depends on application criticality. "
                f"Primary variation source: {max_src}. Further investigation recommended."
            )
        case _:
            thr = result.thresholds_used.get("grr_marginal_pct", 30.0)
            summary = (
                f"The measurement system for <strong>{result.equipment_id}</strong> failed "
                f"GR&R acceptance criteria with %GRR of <strong>{result.percent_grr:.1f}%</strong> "
                f"(threshold: {thr}%). "
                f"This gauge should <strong>NOT</strong> be used for production decisions until corrected."
            )

    anova_html = ""
    if result.anova_table:
        t = result.anova_table
        rows = ""
        for i, src in enumerate(t["source"]):
            ss = f"{t['SS'][i]:.6f}" if t["SS"][i] is not None else "—"
            df_ = str(t["df"][i]) if t["df"][i] is not None else "—"
            ms = f"{t['MS'][i]:.6f}" if t["MS"][i] is not None else "—"
            f_ = f"{t['F'][i]:.4f}" if t["F"][i] is not None else "—"
            p_ = f"{t['p_value'][i]:.4f}" if t["p_value"][i] is not None else "—"
            rows += f"<tr><td>{src}</td><td>{ss}</td><td>{df_}</td><td>{ms}</td><td>{f_}</td><td>{p_}</td></tr>\n"
        anova_html = f"""
        <h2>5. ANOVA Table</h2>
        <table>
          <thead><tr><th>Source</th><th>SS</th><th>df</th><th>MS</th><th>F</th><th>p-value</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    warns_html = "".join(f"<li>⚠ {w}</li>" for w in result.warnings) or "<li>None</li>"
    recs_html = "".join(f"<li>✓ {r}</li>" for r in result.recommendations)
    assum_html = "".join(f"<li>{a}</li>" for a in result.assumptions)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GaugeGuard AI — GR&R Report</title>
<style>
  body{{font-family:Arial,sans-serif;margin:40px;color:#2c3e50;background:#f9f9f9}}
  h1{{color:#2980b9;border-bottom:2px solid #2980b9;padding-bottom:8px}}
  h2{{color:#34495e;margin-top:32px}}
  table{{border-collapse:collapse;width:100%;margin-top:8px}}
  th,td{{border:1px solid #bdc3c7;padding:8px 12px;text-align:left}}
  th{{background:#2980b9;color:white}}
  tr:nth-child(even){{background:#ecf0f1}}
  .badge{{display:inline-block;padding:6px 18px;border-radius:4px;color:white;font-weight:bold;background:{status_color}}}
  .summary{{background:#eaf4fb;border-left:4px solid #2980b9;padding:12px 16px;margin:12px 0}}
  footer{{margin-top:48px;color:#7f8c8d;font-size:12px;border-top:1px solid #bdc3c7;padding-top:8px}}
</style>
</head>
<body>
<h1>🔬 GaugeGuard AI — GR&amp;R Study Report</h1>
<p><strong>Report Date:</strong> {now} &nbsp;|&nbsp; <strong>Study ID:</strong> {result.study_id}</p>

<h2>1. Executive Summary</h2>
<div class="summary"><p>{summary}</p></div>

<h2>2. Study Configuration</h2>
<table>
  <tr><th>Equipment ID</th><td>{result.equipment_id}</td><th>Dataset</th><td>{dataset_name or "—"}</td></tr>
  <tr><th>Method</th><td>{result.method}</td><th>Study k</th><td>{result.thresholds_used.get("study_k",6)}</td></tr>
  <tr><th>Parts</th><td>{result.n_parts}</td><th>Operators</th><td>{result.n_operators}</td></tr>
  <tr><th>Trials</th><td>{result.n_trials}</td><th>Total Measurements</th><td>{result.n_parts * result.n_operators * result.n_trials}</td></tr>
</table>

<h2>3. Variation Results</h2>
<table>
  <thead><tr><th>Component</th><th>Study Variation</th><th>% of Total</th></tr></thead>
  <tbody>
    <tr><td>EV (Repeatability)</td><td>{result.ev_study:.4f}</td><td>{result.percent_ev:.1f}%</td></tr>
    <tr><td>AV (Reproducibility)</td><td>{result.av_study:.4f}</td><td>{result.percent_av:.1f}%</td></tr>
    <tr><td><strong>GRR (Total Gage)</strong></td><td><strong>{result.grr_study:.4f}</strong></td><td><strong>{result.percent_grr:.1f}%</strong></td></tr>
    <tr><td>PV (Part Variation)</td><td>{result.pv_study:.4f}</td><td>{result.percent_pv:.1f}%</td></tr>
    <tr><td>TV (Total Variation)</td><td>{result.tv_study:.4f}</td><td>100.0%</td></tr>
  </tbody>
</table>

<h2>4. Status &amp; NDC</h2>
<p>Status: <span class="badge">{result.status}</span></p>
<p><strong>NDC (Number of Distinct Categories):</strong> {result.ndc}
{"— adequate (≥5)" if result.ndc >= 5 else " — INSUFFICIENT (need ≥5)"}</p>
<p><strong>Interaction pooled:</strong> {result.interaction_pooled}
(p={result.interaction_p_value:.3f})</p>

{anova_html}

<h2>6. Warnings</h2>
<ul>{warns_html}</ul>

<h2>7. Recommendations</h2>
<ul>{recs_html}</ul>

<h2>8. Assumptions &amp; Methodology</h2>
<ul>{assum_html}</ul>

<footer>Generated by GaugeGuard AI | {now}</footer>
</body>
</html>"""
