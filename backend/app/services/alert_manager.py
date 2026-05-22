"""Alert manager — persists, notifies, and deduplicates alerts."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

import httpx

from ..database import SessionLocal
from ..engines.grr_engine import GRRResult
from ..engines.spc_engine import SPCViolation
from ..models.db_models import Alert, Settings
from .audit_service import audit


class AlertManager:
    def __init__(self) -> None:
        self._last_alert: dict[tuple[str, str], datetime] = {}

    def _is_suppressed(self, process_id: str, rule: str, cooldown_minutes: int) -> bool:
        key = (process_id, rule)
        if key in self._last_alert:
            elapsed = datetime.utcnow() - self._last_alert[key]
            if elapsed < timedelta(minutes=cooldown_minutes):
                print(f"[ALERT SUPPRESSED] ({process_id}, {rule}) — cooldown active")
                return True
        return False

    def _record_alert(self, process_id: str, rule: str) -> None:
        self._last_alert[(process_id, rule)] = datetime.utcnow()

    def process_grr_result(self, result: GRRResult) -> list[Alert]:
        alerts = []
        if result.status == "ACCEPTABLE":
            return alerts

        severity = "critical" if result.status == "NOT_ACCEPTABLE" else "warning"
        with SessionLocal() as db:
            settings = db.get(Settings, 1) or Settings()
            cooldown = settings.cooldown_minutes

        if self._is_suppressed(result.equipment_id, "GRR_STATUS", cooldown):
            return alerts

        alert = Alert(
            id=str(uuid.uuid4()),
            created_at=datetime.utcnow(),
            source_type="GRR",
            source_id=result.study_id,
            severity=severity,
            rule_triggered="GRR_STATUS",
            process_id=result.equipment_id,
            observed_value=result.percent_grr,
        )
        with SessionLocal() as db:
            db.add(alert)
            db.commit()
            db.refresh(alert)

        self._record_alert(result.equipment_id, "GRR_STATUS")
        audit.log(
            "ALERT_GENERATED", "Alert", alert.id,
            f"GRR {result.status} for {result.equipment_id} (%GRR={result.percent_grr:.1f}%)",
        )

        with SessionLocal() as db:
            settings = db.get(Settings, 1) or Settings()
        self.notify(alert, settings)
        alerts.append(alert)
        return alerts

    def process_spc_violations(self, violations: list[SPCViolation], source_id: str) -> list[Alert]:
        alerts = []
        with SessionLocal() as db:
            settings = db.get(Settings, 1) or Settings()
            cooldown = settings.cooldown_minutes

        for v in violations:
            if self._is_suppressed(v.process_id, v.rule_triggered, cooldown):
                continue

            alert = Alert(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                source_type="SPC",
                source_id=source_id,
                severity=v.severity,
                rule_triggered=v.rule_triggered,
                process_id=v.process_id,
                observed_value=v.observed_value,
            )
            with SessionLocal() as db:
                db.add(alert)
                db.commit()
                db.refresh(alert)

            self._record_alert(v.process_id, v.rule_triggered)
            audit.log(
                "ALERT_GENERATED", "Alert", alert.id,
                f"SPC {v.rule_triggered} at point {v.point_index} for {v.process_id}",
            )
            self.notify(alert, settings)
            alerts.append(alert)
        return alerts

    def notify(self, alert: Alert, settings: Settings) -> None:
        try:
            if settings.slack_webhook_url:
                self.send_slack(settings.slack_webhook_url, alert)
            else:
                self.send_slack_simulation(alert)

            if settings.smtp_host:
                pass  # real SMTP not wired in demo
            else:
                self.send_email_simulation(alert)
        except Exception as exc:
            print(f"[ALERT NOTIFY ERROR] {exc}")

    def send_slack(self, webhook_url: str, alert: Alert) -> bool:
        msg = {
            "text": (
                f"*GaugeGuard Alert* [{alert.severity.upper()}]\n"
                f"Rule: `{alert.rule_triggered}` | Process: `{alert.process_id}`\n"
                f"Value: `{alert.observed_value}` | ID: `{alert.id}`"
            )
        }
        try:
            r = httpx.post(webhook_url, json=msg, timeout=5)
            return r.status_code == 200
        except Exception as exc:
            print(f"[SLACK ERROR] {exc}")
            return False

    def send_email_simulation(self, alert: Alert) -> None:
        print(
            f"[EMAIL SIMULATED] TO: quality@plant.local | Subject: GaugeGuard Alert [{alert.severity}]\n"
            f"  Rule: {alert.rule_triggered} | Process: {alert.process_id} | Value: {alert.observed_value}"
        )

    def send_slack_simulation(self, alert: Alert) -> None:
        print(
            f"[SLACK SIMULATED] GaugeGuard [{alert.severity.upper()}] "
            f"{alert.rule_triggered} — {alert.process_id} — val={alert.observed_value}"
        )


alert_manager = AlertManager()
