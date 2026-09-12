"""Agent identities — first-class OS users for agents.

Humans authenticate with JWT. Agents authenticate with scoped API keys
(`mag_...`, sha256-hashed at rest, shown once at creation). Either resolves
to an identity dict: {"kind": "human"|"agent", "id": str, "scopes": [...]}.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

KEY_PREFIX = "mag_"
DEFAULT_SCOPES = ["chat", "background", "browser", "memory"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


class AgentIdentityStore:
    def __init__(self, db_path: str = "./data/agents/identities.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = Lock()
        with self.conn:
            self.conn.execute("""CREATE TABLE IF NOT EXISTS agent_identities
                (id TEXT PRIMARY KEY, name TEXT, owner TEXT DEFAULT 'system',
                 scopes TEXT DEFAULT '[]', key_hash TEXT, key_hint TEXT,
                 status TEXT DEFAULT 'active',
                 created_at TEXT, last_used_at TEXT)""")

    def create(self, name: str, owner: str = "system",
               scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create an identity. Returns record WITH the plaintext key (once)."""
        secret = KEY_PREFIX + secrets.token_hex(24)
        aid = "ag_" + secrets.token_hex(4)
        rec = {
            "id": aid,
            "name": name.strip() or aid,
            "owner": owner,
            "scopes": scopes or list(DEFAULT_SCOPES),
            "key_hash": _hash_key(secret),
            "key_hint": secret[:12] + "…",
            "status": "active",
            "created_at": _now(),
            "last_used_at": "",
        }
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT INTO agent_identities VALUES (?,?,?,?,?,?,?,?,?)",
                (rec["id"], rec["name"], rec["owner"], json.dumps(rec["scopes"]),
                 rec["key_hash"], rec["key_hint"], rec["status"],
                 rec["created_at"], rec["last_used_at"]))
        out = self._public(rec)
        out["api_key"] = secret
        return out

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM agent_identities ORDER BY created_at DESC")
            return [self._public(dict(r)) for r in cur.fetchall()]

    def get(self, aid: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cur = self.conn.execute("SELECT * FROM agent_identities WHERE id=?", (aid,))
            r = cur.fetchone()
            return self._public(dict(r)) if r else None

    def revoke(self, aid: str) -> bool:
        with self._lock, self.conn:
            cur = self.conn.execute(
                "UPDATE agent_identities SET status='revoked' WHERE id=? AND status='active'", (aid,))
            return cur.rowcount > 0

    def verify(self, secret: str) -> Optional[Dict[str, Any]]:
        """Check a presented key. Returns public identity (no hash) or None."""
        if not secret or not secret.startswith(KEY_PREFIX):
            return None
        digest = _hash_key(secret)
        with self._lock, self.conn:
            cur = self.conn.execute(
                "SELECT * FROM agent_identities WHERE key_hash=? AND status='active'", (digest,))
            r = cur.fetchone()
            if not r:
                return None
            self.conn.execute("UPDATE agent_identities SET last_used_at=? WHERE id=?",
                              (_now(), r["id"]))
            return self._public(dict(r))

    @staticmethod
    def _public(d: Dict[str, Any]) -> Dict[str, Any]:
        d = dict(d)
        d.pop("key_hash", None)
        sc = d.get("scopes")
        if isinstance(sc, list):
            d["scopes"] = sc
        else:
            try:
                d["scopes"] = json.loads(sc or "[]")
            except Exception:
                d["scopes"] = []
        return d


_store: Optional[AgentIdentityStore] = None


def get_identity_store(db_path: Optional[str] = None) -> AgentIdentityStore:
    global _store
    if _store is None or db_path:
        _store = AgentIdentityStore(db_path or "./data/agents/identities.db")
    return _store
