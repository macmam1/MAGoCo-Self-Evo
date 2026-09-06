"""Planning persistence — SQLite-backed plan store (crash-safe, restart-safe).

Design (PlanDB lesson): plans are living hypotheses stored durably, not
in-memory dicts. Full plan JSON blob + queryable indexes + append-only events.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing Dict, List, Optional


class PlanStore:
    """Durable store for plans, tasks (inside plan blob), and execution events."""

    def __init__(self, db_path: str = "./data/planning/plans.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS plans
            (id TEXT PRIMARY KEY, name TEXT, layer TEXT DEFAULT 'os',
             project_id TEXT, status TEXT DEFAULT 'draft',
             created_at TEXT, updated_at TEXT, data_json TEXT DEFAULT '{}')""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_plans_layer ON plans(layer)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_plans_project ON plans(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status)")
        cur.execute("""CREATE TABLE IF NOT EXISTS plan_events
            (id INTEGER PRIMARY KEY AUTOINCREMENT, plan_id TEXT NOT NULL,
             created_at TEXT, kind TEXT, detail TEXT)""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_events_plan ON plan_events(plan_id)")
        self.conn.commit()

    @contextmanager
    def _cur(self):
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def save(self, plan_dict: Dict) -> None:
        """Upsert a full plan snapshot."""
        with self._cur() as cur:
            cur.execute("""INSERT INTO plans (id,name,layer,project_id,status,created_at,updated_at,data_json)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET name=excluded.name, layer=excluded.layer,
                project_id=excluded.project_id, status=excluded.status,
                updated_at=excluded.updated_at, data_json=excluded.data_json""",
                (plan_dict["id"], plan_dict.get("name", ""), plan_dict.get("layer", "os"),
                 plan_dict.get("project_id"), plan_dict.get("status", "draft"),
                 plan_dict.get("created_at", datetime.utcnow().isoformat()),
                 plan_dict.get("updated_at", datetime.utcnow().isoformat()),
                 json.dumps(plan_dict)))

    def load(self, plan_id: str) -> Optional[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT data_json FROM plans WHERE id=?", (plan_id,))
            row = cur.fetchone()
            return json.loads(row["data_json"]) if row else None

    def delete(self, plan_id: str) -> bool:
        with self._cur() as cur:
            cur.execute("DELETE FROM plans WHERE id=?", (plan_id,))
            return cur.rowcount > 0

    def list(self, layer: Optional[str] = None, project_id: Optional[str] = None,
             limit: int = 200) -> List[Dict]:
        with self._cur() as cur:
            q = "SELECT data_json FROM plans WHERE 1=1"
            params: list = []
            if layer:
                q += " AND layer=?"
                params.append(layer)
            if project_id:
                q += " AND project_id=?"
                params.append(project_id)
            q += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            cur.execute(q, params)
            return [json.loads(r["data_json"]) for r in cur.fetchall()]

    def log_event(self, plan_id: str, kind: str, detail: str = "") -> None:
        with self._cur() as cur:
            cur.execute("INSERT INTO plan_events (plan_id, created_at, kind, detail) VALUES (?,?,?,?)",
                        (plan_id, datetime.utcnow().isoformat(), kind, detail[:2000]))

    def events(self, plan_id: str, limit: int = 200) -> List[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM plan_events WHERE plan_id=? ORDER BY id DESC LIMIT ?",
                        (plan_id, limit))
            return [dict(r) for r in cur.fetchall()]


_store: Optional[PlanStore] = None


def get_plan_store(db_path: Optional[str] = None) -> PlanStore:
    global _store
    if _store is None:
        _store = PlanStore(db_path or "./data/planning/plans.db")
    return _store
