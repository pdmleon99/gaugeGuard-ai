from __future__ import annotations
from pydantic import BaseModel


class GRRAnalyzeRequest(BaseModel):
    dataset_id: str
    method: str = "ANOVA"
    equipment_id: str = "CMM-001"
    thresholds: dict | None = None


class GRRStudySummary(BaseModel):
    id: str
    created_at: str
    equipment_id: str
    status: str
    percent_grr: float
    ndc: int
    method: str
    dataset_name: str


class GRRStudyList(BaseModel):
    items: list[GRRStudySummary]
    total: int
