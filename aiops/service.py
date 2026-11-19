"""In-process incident state, HITL approvals, and audit logging.

Local demonstration only: for multi-user production, replace with authenticated
roles, a transactional database, distributed idempotency, and an approval service.
"""
from __future__ import annotations

import copy
import json
import secrets
import threading
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .core import RemediationError, revoke_ssh_world_localstack, utc_now, validate_security_group_id
from .integrations import ROOT, localstack_client, optional_ai_summary, retrieve_runbook

DEMO_INCIDENTS: list[dict[str, Any]] = [
    {"id": "INC-2401", "title": "SSH exposed to public internet", "description": "Unauthorized SSH brute-force attempt detected. TCP port 22 open to 0.0.0.0/0.",
     "resource": "sg-0a1b2c3d", "service": "EC2 / Security Groups", "severity": "Critical", "status": "Open",
     "origin": "Cloud posture monitor", "ip": "198.51.100.24", "observed": "2026-11-19T08:22:00Z", "actionable": True},
    {"id": "INC-2402", "title": "Unrestricted database egress", "description": "An outbound database rule permits external destinations. Manual investigation required.",
     "resource": "sg-12ab34cd", "service": "VPC / Network Controls", "severity": "High", "status": "Investigating",
     "origin": "Policy scan", "ip": "—", "observed": "2026-11-19T07:42:00Z", "actionable": False},
    {"id": "INC-2403", "title": "Missing S3 access logging", "description": "Bucket access logs are not enabled. No automatic playbook is registered.",
     "resource": "arn:aws:s3:::demo-logs", "service": "S3 / Storage", "severity": "Medium", "status": "Open",
     "origin": "Configuration scan", "ip": "—", "observed": "2026-11-19T06:50:00Z", "actionable": False},
    {"id": "INC-2404", "title": "Excessive IAM permissions", "description": "An example IAM policy was flagged and reviewed.",
     "resource": "role/demo-ci", "service": "IAM / Identity", "severity": "High", "status": "Resolved",
     "origin": "Risk engine", "ip": "—", "observed": "2026-11-18T18:24:00Z", "actionable": False},
    {"id": "INC-2405", "title": "Unencrypted EBS snapshot", "description": "A demonstration snapshot was found without encryption.",
     "resource": "snap-04e1a2b3", "service": "EC2 / Storage", "severity": "Low", "status": "Resolved",
     "origin": "Posture monitor", "ip": "—", "observed": "2026-11-18T12:12:00Z", "actionable": False},
]


class OperationsService:
    def __init__(self, mode: str = "demo", alert_path: Path | None = None, ec2_factory=None, clock=time.monotonic):
        if mode not in {"demo", "localstack"}:
            raise ValueError("Mode must be demo or localstack")
        self.mode = mode
        self._lock = threading.RLock()
        self._clock = clock
        self._ec2_factory = ec2_factory or localstack_client
        self._alert_path = alert_path or ROOT / "cloud_alert.json"
        self._incidents = copy.deepcopy(DEMO_INCIDENTS) if mode == "demo" else []
        self._verified_resources: set[str] = set()
        self._plans: dict[str, dict[str, Any]] = {}
        self._approvals: dict[str, dict[str, Any]] = {}
        self._audit: list[dict[str, Any]] = []
        self._audit_event("SYSTEM_STARTED", "System", "ok", f"{mode.upper()} mode initialized")

    def _audit_event(self, action: str, target: str, outcome: str, detail: str):
        self._audit.append({"event_id": "EVT-" + secrets.token_hex(4).upper(),
                            "timestamp": utc_now(), "actor": "Local operator", "action": action,
                            "resource": target, "outcome": outcome, "detail": detail[:350]})
        self._audit = self._audit[-200:]

    def _current_incidents(self):
        if self.mode == "demo":
            return copy.deepcopy(self._incidents)
        if not self._alert_path.exists():
            return []
        try:
            raw = json.loads(self._alert_path.read_text(encoding="utf-8"))
            group_id = validate_security_group_id(raw.get("affected_resource_id"))
            return [{"id": str(raw.get("alert_id", "ALT-LOCAL"))[:64],
                     "title": "SSH exposure security alert",
                     "description": str(raw.get("description", "Public SSH exposure"))[:1000],
                     "resource": group_id, "service": "EC2 / Security Groups",
                     "severity": str(raw.get("severity", "Critical")).capitalize(),
                     "status": "Resolved" if group_id in self._verified_resources else "Open", "origin": "LocalStack alert file",
                     "ip": str(raw.get("attacker_ip", "—"))[:45],
                     "observed": str(raw.get("timestamp", ""))[:32], "actionable": True}]
        except (OSError, ValueError, TypeError, RemediationError):
            return []

    def overview(self):
        with self._lock:
            incidents = self._current_incidents()
            open_items = [i for i in incidents if i["status"] not in ("Resolved", "Mitigated")]
            distribution = Counter(i["severity"] for i in incidents)
            summary = {"total": len(incidents), "active": len(open_items),
                       "critical": sum(i["severity"].lower() == "critical" for i in open_items),
                       "resolved": len(incidents) - len(open_items)}
            return {"mode": self.mode, "environment": "Simulated lab" if self.mode == "demo" else "LocalStack · local only",
                    "demo_notice": self.mode == "demo", "incidents": incidents, "summary": summary,
                    "severity_distribution": [{"severity": s, "count": distribution.get(s, 0)}
                                              for s in ("Critical", "High", "Medium", "Low")],
                    "audit": list(reversed(copy.deepcopy(self._audit))), "runbook_available": (ROOT / "company_docs" / "SOP_SentinelOps_Demo.md").exists(),
                    "capabilities": {"real_aws": False, "automated_execution": self.mode == "localstack",
                                     "human_approval": True, "safe_demo": self.mode == "demo"}}

    def health(self):
        with self._lock:
            data = {"api": "online", "mode": self.mode, "aws_production": "disabled",
                    "approval_gate": "enforced", "llm": "optional", "retrieval": "available as local runbook",
                    "last_checked": utc_now()}
            if self.mode == "localstack":
                data["localstack"] = "configured; connectivity checked only during execution"
                data["alert_file"] = "found" if self._alert_path.exists() else "missing: run master_setup.py"
            else:
                data["localstack"] = "not required for demo"
            return data

    def _lookup(self, incident_id: str):
        item = next((x for x in self._current_incidents() if x["id"] == incident_id), None)
        if not item:
            raise RemediationError("Incident not found.")
        return item

    def runbooks(self):
        return retrieve_runbook("SSH port 22 public access security group incident response")

    def analyze(self, incident_id: str):
        with self._lock:
            item = self._lookup(incident_id)
            if not item["actionable"]:
                raise RemediationError("No approved automated playbook exists for this incident. Use manual investigation.")
            if item["status"] == "Resolved":
                raise RemediationError("Incident is resolved. No new remediation plan is allowed.")
            group_id = validate_security_group_id(item["resource"])
            runbook = retrieve_runbook(item["description"])
            if not runbook["body"]:
                raise RemediationError("Required security runbook is missing. No plan can be issued.")
            plan_id = "PLN-" + secrets.token_hex(5).upper()
            plan = {"id": plan_id, "incident_id": incident_id, "resource": group_id,
                    "title": "Remove public IPv4 SSH ingress", "operation": "revoke_world_ssh_v4",
                    "description": "Remove TCP port 22 access from 0.0.0.0/0 on this exact security group. Preserve unrelated rules.",
                    "risk": "Medium", "state": "Awaiting approval", "created_at": utc_now(),
                    "steps": ["Validate the exact security-group ID", "Read and inspect current ingress rules",
                              "Revoke only TCP/22 from 0.0.0.0/0", "Read rules again and verify public SSH access is absent"],
                    "change": {"before": "tcp/22 · 0.0.0.0/0 · ALLOW", "after": "tcp/22 · 0.0.0.0/0 · REVOKED"},
                    "approval_phrase": f"REVOKE SSH {group_id}",
                    "runbook": runbook,
                    "ai_summary": optional_ai_summary(item["description"], runbook["body"])}
            self._plans[plan_id] = {"plan": plan, "created": self._clock()}
            self._audit_event("PLAN_CREATED", group_id, "pending", f"Plan {plan_id} created for {incident_id}")
            return copy.deepcopy(plan)

    def _require_plan(self, plan_id: str):
        stored = self._plans.get(plan_id)
        if not stored or self._clock() - stored["created"] > 600:
            raise RemediationError("Plan does not exist or has expired (10-minute limit). Re-analyze the incident.")
        return stored["plan"]

    def approve(self, plan_id: str, confirmation: str, acknowledged: bool):
        with self._lock:
            plan = self._require_plan(plan_id)
            current = self._lookup(plan["incident_id"])
            if current["status"] == "Resolved":
                raise RemediationError("Incident is no longer open.")
            if acknowledged is not True or confirmation != plan["approval_phrase"]:
                self._audit_event("APPROVAL_REJECTED", plan["resource"], "denied", "Operator confirmation did not match")
                raise RemediationError("Authorization rejected. Check the acknowledgment and type the exact approval phrase.")
            token = secrets.token_urlsafe(32)
            self._approvals[token] = {"plan_id": plan_id, "expires": self._clock() + 120, "consumed": False}
            self._audit_event("PLAN_APPROVED", plan["resource"], "approved", f"One-use approval issued for {plan_id}")
            return {"approval_token": token, "expires_in_seconds": 120, "plan_id": plan_id}

    def execute(self, plan_id: str, approval_token: str):
        with self._lock:
            plan = self._require_plan(plan_id)
            approval = self._approvals.get(approval_token)
            if not approval or approval["plan_id"] != plan_id or approval["consumed"] or self._clock() >= approval["expires"]:
                raise RemediationError("Execution blocked: a valid, unused, unexpired approval is required.")
            approval["consumed"] = True  # Single-use, even on failure.
            incident = self._lookup(plan["incident_id"])
            if incident["status"] == "Resolved" or incident["resource"].lower() != plan["resource"]:
                raise RemediationError("Incident state changed; analyze and approve a new plan.")
            try:
                if self.mode == "demo":
                    for record in self._incidents:
                        if record["id"] == incident["id"]:
                            record["status"] = "Resolved"
                    outcome = {"status": "remediated", "verified": True,
                               "message": "Simulation complete: example public TCP/22 rule removed and verified in demo state."}
                else:
                    outcome = revoke_ssh_world_localstack(plan["resource"], self._ec2_factory())
                plan["state"] = "Verified" if outcome["verified"] else "Failed"
                if self.mode == "localstack" and outcome["verified"]:
                    self._verified_resources.add(plan["resource"])
                self._audit_event("REMEDIATION_EXECUTED", plan["resource"], outcome["status"], outcome["message"])
                return {**outcome, "simulation": self.mode == "demo", "plan_id": plan_id,
                        "resource": plan["resource"], "completed_at": utc_now()}
            except RemediationError as error:
                plan["state"] = "Failed"
                self._audit_event("REMEDIATION_FAILED", plan["resource"], "failed", str(error))
                raise

    def reset_demo(self):
        with self._lock:
            if self.mode != "demo":
                raise RemediationError("Demo reset is unavailable outside demo mode.")
            self._incidents = copy.deepcopy(DEMO_INCIDENTS)
            self._plans.clear()
            self._approvals.clear()
            self._audit_event("DEMO_RESET", "Simulation", "ok", "Sample incidents restored; approvals invalidated")
            return {"message": "Demo reset successfully."}
