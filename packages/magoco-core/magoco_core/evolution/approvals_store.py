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
               proposed_input: Optional[Dict] = None) -> Dict:
        rid = uuid.uuid4().hex[:8]
        now = datetime.utcnow().isoformat()
        with self._cur() as cur:
            cur.execute("INSERT INTO approvals VALUES (?,?,?,?,?,?,?,?)",
                        (rid, agent_name, action_description,
                         json.dumps(proposed_input or {}), "pending", now, None, None))
        return self.get(rid)

    def get(self, request_id: str) -> Optional[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM approvals WHERE request_id=?", (request_id,))
            r = cur.fetchone()
            if not r:
                return None
            d = dict(r)
            d["proposed_input"] = json.loads(d["proposed_input"] or "{}")
            return d

    def list(self, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with self._cur() as cur:
            if status:
                cur.execute("SELECT * FROM approvals WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit))
            else:
                cur.execute("SELECT * FROM approvals ORDER BY created_at DESC LIMIT ?", (limit,))
            out = []
            for r in cur.fetchall():
                d = dict(r)
                d["proposed_input"] = json.loads(d["proposed_input"] or "{}")
                out.append(d)
            return out

    def find_by_ref(self, ref_key: str, ref_value: str) -> List[Dict]:
        """Find approvals whose proposed_input contains ref_key=ref_value."""
        out = []
        for r in self.list(limit=500):
            if str(r.get("proposed_input", {}).get(ref_key)) == str(ref_value):
                out.append(r)
        return out

    def resolve(self, request_id: str, status: str, comment: Optional[str] = None) -> Optional[Dict]:
        if status not in ("approved", "rejected", "skipped"):
            raise ValueError("invalid status")
        with self._cur() as cur:
            cur.execute("UPDATE approvals SET status=?, resolved_at=?, comment=? WHERE request_id=?",
                        (status, datetime.utcnow().isoformat(), comment, request_id))
            if cur.rowcount == 0:
                return None
        return self.get(request_id)


_store = None

def get_approvals_store(db_path: Optional[str] = None):
    global _store
    if _store is None:
        _store = ApprovalsStore(db_path or "./data/approvals/approvals.db")
    return _store
