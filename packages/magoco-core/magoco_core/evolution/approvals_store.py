"""Persistent approvals store (SQLite) backing the Approvals tab + Growth gating."""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ApprovalsStore:
    def __init__(self, db_path: str = "./data/approvals/approvals.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS approvals
            (request_id TEXT PRIMARY KEY, agent_name TEXT, action_description TEXT,
             proposed_input TEXT, status TEXT DEFAULT 'pending',
             created_at TEXT, resolved_at TEXT, comment TEXT)""")
        # v2 columns: tool context + risk + expiry + decider (backward compatible)
        for col, ddl in [
            ("tool_name", "TEXT DEFAULT ''"),
            ("args_json", "TEXT DEFAULT '{}'"),
            ("action", "TEXT DEFAULT ''"),
            ("resource", "TEXT DEFAULT ''"),
            ("session_id", "TEXT DEFAULT ''"),
            ("risk", "TEXT DEFAULT ''"),
            ("risk_score", "INTEGER DEFAULT 0"),
            ("expires_at", "TEXT"),
            ("decided_by", "TEXT DEFAULT ''"),
        ]:
            try:
                cur.execute(f"ALTER TABLE approvals ADD COLUMN {col} {ddl}")
            except Exception:
                pass
        cur.execute("CREATE INDEX IF NOT EXISTS idx_appr_status ON approvals(status)")
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

    def create(self, agent_name: str, action_description: str,
               proposed_input: Optional[Dict] = None,
               tool_name: str = "", args: Optional[Dict] = None,
               action: str = "", resource: str = "", session_id: str = "",
               risk: str = "", risk_score: int = 0,
               ttl_seconds: int = 600) -> Dict:
        from datetime import timedelta
        rid = uuid.uuid4().hex[:8]
        now = datetime.utcnow()
        expires = (now + timedelta(seconds=ttl_seconds)).isoformat() if ttl_seconds > 0 else None
        with self._cur() as cur:
            cur.execute("""INSERT INTO approvals
                (request_id, agent_name, action_description, proposed_input, status,
                 created_at, resolved_at, comment, tool_name, args_json, action,
                 resource, session_id, risk, risk_score, expires_at, decided_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (rid, agent_name, action_description,
                 json.dumps(proposed_input or {}), "pending", now.isoformat(), None, None,
                 tool_name, json.dumps(args or {}), action, resource, session_id,
                 risk, risk_score, expires, ""))
        return self.get(rid)

    def _parse(self, r: sqlite3.Row) -> Dict:
        d = dict(r)
        d["proposed_input"] = json.loads(d.get("proposed_input") or "{}")
        try:
            d["args"] = json.loads(d.get("args_json") or "{}")
        except Exception:
            d["args"] = {}
        return d

    def get(self, request_id: str) -> Optional[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,))
            r = cur.fetchone()
            if not r:
                return None
            return self._parse(r)

    def list(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with self._cur() as cur:
            if status:
                cur.execute("SELECT * FROM approvals WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit))
            else:
                cur.execute("SELECT * FROM approvals ORDER BY created_at DESC LIMIT ?", (limit,))
            return [self._parse(r) for r in cur.fetchall()]

    def find_by_ref(self, ref_key: str, ref_value: str) -> List[Dict]:
        """Find approvals whose proposed_input contains ref_key=ref_value."""
        out = []
        for r in self.list(limit=500):
            if str(r.get("proposed_input", {}).get(ref_key)) == str(ref_value):
                out.append(r)
        return out

    def resolve(self, request_id: str, status: str, comment: Optional[str] = None,
                decided_by: str = "") -> Optional[Dict]:
        if status not in ("approved", "rejected", "skipped", "expired"):
            raise ValueError("invalid status")
        with self._cur() as cur:
            cur.execute("UPDATE approvals SET status=?, resolved_at=?, comment=?, decided_by=? WHERE request_id=?",
                        (status, datetime.utcnow().isoformat(), comment, decided_by, request_id))
            if cur.rowcount == 0:
                return None
        return self.get(request_id)

    def sweep_expired(self, limit: int = 100) -> int:
        """Auto-expire stale pending approvals. Returns count expired."""
        now = datetime.utcnow().isoformat()
        with self._cur() as cur:
            cur.execute("""SELECT request_id FROM approvals WHERE status='pending'
                AND expires_at IS NOT NULL AND expires_at < ? LIMIT ?""", (now, limit))
            ids = [r["request_id"] for r in cur.fetchall()]
        for rid in ids:
            self.resolve(rid, "expired", comment="auto-expired: no decision in time")
        return len(ids)


_store = None

def get_approvals_store(db_path: Optional[str] = None):
    global _store
    if _store is None:
        _store = ApprovalsStore(db_path or "./data/approvals/approvals.db")
    return _store
