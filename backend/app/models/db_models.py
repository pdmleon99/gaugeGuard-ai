"""SQLAlchemy 2.0 ORM models — SQLite local, PostgreSQL-compatible schema."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, Integer, String, Text, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class GRRStudy(Base):
    __tablename__ = "grr_studies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    equipment_id: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    percent_grr: Mapped[float] = mapped_column(Float)
    ndc: Mapped[int] = mapped_column(Integer)
    n_parts: Mapped[int] = mapped_column(Integer)
    n_operators: Mapped[int] = mapped_column(Integer)
    n_trials: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(20))
    result_json: Mapped[str] = mapped_column(Text)
    calculation_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    dataset_name: Mapped[str] = mapped_column(String(200), default="")


class SPCAnalysis(Base):
    __tablename__ = "spc_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    process_id: Mapped[str] = mapped_column(String(100))
    chart_type: Mapped[str] = mapped_column(String(20))
    n_violations: Mapped[int] = mapped_column(Integer, default=0)
    process_status: Mapped[str] = mapped_column(String(30))
    result_json: Mapped[str] = mapped_column(Text)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_type: Mapped[str] = mapped_column(String(10))  # "GRR" | "SPC"
    source_id: Mapped[str] = mapped_column(String(36))
    severity: Mapped[str] = mapped_column(String(20))
    rule_triggered: Mapped[str] = mapped_column(String(50))
    process_id: Mapped[str] = mapped_column(String(100))
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(30), nullable=True)
    feedback_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_type: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(100), default="")
    user_source: Mapped[str] = mapped_column(String(60), default="system")
    status: Mapped[str] = mapped_column(String(20), default="success")
    message: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    grr_acceptable_pct: Mapped[float] = mapped_column(Float, default=10.0)
    grr_marginal_pct: Mapped[float] = mapped_column(Float, default=30.0)
    ndc_minimum: Mapped[int] = mapped_column(Integer, default=5)
    study_k: Mapped[int] = mapped_column(Integer, default=6)
    alpha_interaction: Mapped[float] = mapped_column(Float, default=0.25)
    baseline_n_spc: Mapped[int] = mapped_column(Integer, default=25)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    slack_webhook_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    smtp_host: Mapped[str | None] = mapped_column(String(200), nullable=True)
    smtp_port: Mapped[int] = mapped_column(Integer, default=587)
    demo_mode: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
