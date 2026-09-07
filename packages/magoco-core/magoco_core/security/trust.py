"""Trust registry — earned autonomy per (actor, action).

Atom lesson: autonomy is earned from VERIFIED outcomes, never self-reported,
and auto-revoked on regression. An ASK rule relaxes to allow-by-trust only when:
- verified_ok >= threshold (default 10), AND
- recent failure rate is low (last 20 outcomes, <10% fail).

Trust never overrides DENY or critical-risk auto-deny. All relaxations are
audited. Opt-in per call (executor flag), off by default.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class TrustRegistry:
    def __init__(self, db_path: str = "./data/approvals/trust.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS outcomes
            (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT,
             ok INTEGER, verified INTEGER DEFAULT 1, created_at TEXT)""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_trust_actor_action ON outcomes(actor, action)")
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

    def record(self, actor: str, action: str, ok: bool, verified: bool = True) -> None:
        """Record a VERIFIED outcome (from postcondition check or human approval result)."""
        with self._cur() as cur:
            cur.execute("INSERT INTO outcomes (actor, action, ok, verified, created_at) VALUES (?,?,?,?,?)",
                        (actor, action, int(ok), int(verified), datetime.utcnow().isoformat()))

    def score(self, actor: str, action: str, window: int = 20) -> Dict:
        with self._cur() as cur:
            cur.execute("""SELECT ok, verified FROM outcomes WHERE actor=? AND action=?
                ORDER BY id DESC LIMIT ?""", (actor, action, window))
            rows = cur.fetchall()
        verified_rows = [r for r in rows if r["verified"]]
        oks = sum(1 for r in verified_rows if r["ok"])
        total = len(verified_rows)
        return {
            "actor": actor, "action": action,
            "verified_ok": oks, "verified_total": total,
            "fail_rate": round(1 - oks / total, 2) if total else 1.0,
        }

    def should_relax(self, actor: str, action: str, threshold: int = 10,
                     max_fail_rate: float = 0.1) -> Dict:
        """Should an ASK rule relax to allow-by-trust for this actor+action?"""
        s = self.score(actor, action)
        ok = s["verified_ok"] >= threshold and s["fail_rate"] <= max_fail_rate
        return {**s, "relax": ok, "threshold": threshold,
                "reason": "earned" if ok else "insufficient-verified-history"}

    def reset(self, actor: str = "", action: str = "") -> int:
        """Revoke trust (on regression or manually). Returns rows cleared."""
        with self._cur() as cur:
            if actor and action:
                cur.execute("DELETE FROM outcomes WHERE actor=? AND action=?", (actor, action))
            elif actor:
                cur.execute("DELETE FROM outcomes WHERE actor=?", (actor,))
            else:
                cur.execute("DELETE FROM outcomes")
            return cur.rowcount


_registry: Optional[TrustRegistry] = None


def get_trust_registry(db_path: Optional[str] = None) -> TrustRegistry:
    global _registry
    if _registry is None:
        _registry = TrustRegistry(db_path or "./data/approvals/trust.db")
    return _registry
