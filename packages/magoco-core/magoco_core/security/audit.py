"""Append-only JSONL audit log for every tool decision."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class AuditEvent:
    ts: float
    actor: str
    action: str
    resource: str
    decision: str
    detail: str = ""


class AuditLog:
    def __init__(self, path: str = "project_state/audit.jsonl"):
        self.path = Path(path)

    def append(self, event: AuditEvent) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(event)) + "\n")
        except Exception:
            pass  # audit must never break execution

    def log(self, actor: str, action: str, resource: str, decision: str, detail: str = "") -> None:
        self.append(AuditEvent(time.time(), actor, action, resource, decision, detail))
