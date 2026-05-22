"""Shared style constants for the Streamlit frontend."""
SEVERITY_COLORS = {
    "critical": "#e74c3c",
    "warning": "#f39c12",
    "info": "#3498db",
}

STATUS_COLORS = {
    "ACCEPTABLE": "#27ae60",
    "MARGINAL": "#f39c12",
    "NOT_ACCEPTABLE": "#e74c3c",
    "IN_CONTROL": "#27ae60",
    "WARNING": "#f39c12",
    "OUT_OF_CONTROL": "#e74c3c",
}

CSS = """
<style>
  .badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 4px;
    color: white;
    font-weight: bold;
    font-size: 14px;
  }
</style>
"""


def status_badge(status: str) -> str:
    color = STATUS_COLORS.get(status, "#7f8c8d")
    return f'<span class="badge" style="background:{color}">{status}</span>'
