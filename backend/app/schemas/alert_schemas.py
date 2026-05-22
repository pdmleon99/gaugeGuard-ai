from __future__ import annotations
from pydantic import BaseModel


class AlertFeedbackRequest(BaseModel):
    feedback: str
    comment: str | None = None


class AlertStats(BaseModel):
    total: int
    relevant: int
    false_positive: int
    relevance_rate: float
    fp_rate: float
