from __future__ import annotations
from pydantic import BaseModel


class SPCAnalyzeRequest(BaseModel):
    dataset_id: str
    process_id: str = "LINE-A"
    subgroup_size: int = 5
    enabled_rules: dict | None = None


class SPCAnalysisSummary(BaseModel):
    id: str
    created_at: str
    process_id: str
    chart_type: str
    n_violations: int
    process_status: str
