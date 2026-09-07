"""Provider Groups store — SQLite-backed, survives restarts.

Same pattern as PlanStore: full JSON blob + queryable indexes.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class ProviderGroupStore:
    def __init__(self, db_path: str = "./data/providers/groups.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS provider_groups
            (id TEXT PRIMARY KEY, name TEXT, data_json TEXT,
             created_at TEXT, updated_at TEXT)""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_pgroups_name ON provider_groups(name)")
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

    def create(self, group: Dict) -> Dict:
        gid = group.get("id") or uuid.uuid4().hex[:8]
        group["id"] = gid
        now = datetime.utcnow().isoformat()
        group.setdefault("created_at", now)
        group["updated_at"] = now
        with self._cur() as cur:
            cur.execute("INSERT OR REPLACE INTO provider_groups VALUES (?,?,?,?,?)",
                        (gid, group.get("name", ""), json.dumps(group),
                         group["created_at"], group["updated_at"]))
        return group

    def get(self, gid: str) -> Optional[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT data_json FROM provider_groups WHERE id=?", (gid,))
            row = cur.fetchone()
            return json.loads(row["data_json"]) if row else None

    def list(self) -> List[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT data_json FROM provider_groups ORDER BY updated_at DESC")
            return [json.loads(r["data_json"]) for r in cur.fetchall()]

    def update(self, gid: str, fields: Dict) -> Optional[Dict]:
        existing = self.get(gid)
        if not existing:
            return None
        existing.update({k: v for k, v in fields.items() if v is not None})
        existing["updated_at"] = datetime.utcnow().isoformat()
        with self._cur() as cur:
            cur.execute("UPDATE provider_groups SET name=?, data_json=?, updated_at=? WHERE id=?",
                        (existing.get("name", ""), json.dumps(existing),
                         existing["updated_at"], gid))
        return existing

    def delete(self, gid: str) -> bool:
        with self._cur() as cur:
            cur.execute("DELETE FROM provider_groups WHERE id=?", (gid,))
            return cur.rowcount > 0


_store: Optional[ProviderGroupStore] = None


def get_group_store(db_path: Optional[str] = None) -> ProviderGroupStore:
    global _store
    if _store is None:
        _store = ProviderGroupStore(db_path or "./data/providers/groups.db")
    return _store
