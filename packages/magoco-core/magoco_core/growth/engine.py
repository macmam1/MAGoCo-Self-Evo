"""Growth engine - mines usage patterns, emits suggestions + growth log."""

import json
import logging
import sqlite3
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import UsageEvent, Pattern, GrowthSuggestion, GrowthEvent, GrowthEventType, SuggestionStatus

logger = logging.getLogger(__name__)


class GrowthEngine:
    def __init__(self, db_path: str = "./data/growth/growth.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS usage_events
            (id TEXT PRIMARY KEY, agent_id TEXT, action TEXT, target TEXT, params TEXT, timestamp TEXT, session_id TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS patterns
            (id TEXT PRIMARY KEY, sequence TEXT, count INTEGER, last_seen TEXT, confidence REAL, example_params TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS suggestions
            (id TEXT PRIMARY KEY, kind TEXT, title TEXT, description TEXT, pattern_id TEXT, draft TEXT, status TEXT, created_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS growth_log
            (id TEXT PRIMARY KEY, type TEXT, title TEXT, detail TEXT, ref_id TEXT, created_at TEXT)""")
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

    def record(self, event: UsageEvent) -> str:
        with self._cur() as cur:
            cur.execute("INSERT INTO usage_events VALUES (?,?,?,?,?,?,?)",
                        (event.id, event.agent_id, event.action, event.target,
                         json.dumps(event.params), event.timestamp.isoformat(), event.session_id))
        return event.id

    def mine_patterns(self, min_count: int = 3, seq_len: int = 3) -> List[Pattern]:
        with self._cur() as cur:
            cur.execute("SELECT action,target,params,timestamp FROM usage_events ORDER BY timestamp LIMIT 2000")
            rows = cur.fetchall()
        seqs = [f"{r['action']}:{r['target']}" for r in rows]
        counts = Counter(tuple(seqs[i:i + seq_len]) for i in range(len(seqs) - seq_len + 1))
        out = []
        for seq, cnt in counts.items():
            if cnt < min_count:
                continue
            conf = min(0.95, 0.4 + cnt * 0.1)
            p = Pattern(sequence=list(seq), count=cnt, confidence=conf)
            out.append(p)
            with self._cur() as cur:
                cur.execute("INSERT OR REPLACE INTO patterns VALUES (?,?,?,?,?,?)",
                            (p.id, json.dumps(p.sequence), p.count, p.last_seen.isoformat(), p.confidence, "{}"))
        return sorted(out, key=lambda x: x.count, reverse=True)

    def suggest_from_patterns(self) -> List[GrowthSuggestion]:
        patterns = self.mine_patterns()
        suggestions = []
        for p in patterns[:5]:
            title = f"Automate: {' → '.join(p.sequence)} (×{p.count})"
            draft = {
                "name": f"auto-skill-{p.id[:8]}",
                "steps": [{"action": s.split(':')[0], "target": s.split(':')[1] if ':' in s else ""} for s in p.sequence],
                "trigger_count": p.count,
            }
            s = GrowthSuggestion(kind="auto_skill", title=title,
                                 description=f"Seen {p.count} times, confidence {p.confidence:.0%}. Approve to draft a skill.",
                                 pattern_id=p.id, draft=draft)
            with self._cur() as cur:
                cur.execute("INSERT INTO suggestions VALUES (?,?,?,?,?,?,?,?)",
                            (s.id, s.kind, s.title, s.description, s.pattern_id,
                             json.dumps(s.draft), s.status.value, s.created_at.isoformat()))
            self.log(GrowthEventType.PATTERN_FOUND, title, s.description, ref_id=s.id)
            suggestions.append(s)
        return suggestions

    def list_suggestions(self, status: Optional[str] = None) -> List[Dict]:
        with self._cur() as cur:
            if status:
                cur.execute("SELECT * FROM suggestions WHERE status=? ORDER BY created_at DESC", (status,))
            else:
                cur.execute("SELECT * FROM suggestions ORDER BY created_at DESC LIMIT 50")
            return [dict(r) for r in cur.fetchall()]

    def set_suggestion_status(self, sid: str, status: str) -> bool:
        with self._cur() as cur:
            cur.execute("UPDATE suggestions SET status=? WHERE id=?", (status, sid))
            return cur.rowcount > 0

    def log(self, etype: GrowthEventType, title: str, detail: str = "", ref_id: Optional[str] = None):
        with self._cur() as cur:
            cur.execute("INSERT INTO growth_log VALUES (?,?,?,?,?,?)",
                        (__import__("uuid").uuid4().hex[:8], etype.value, title, detail, ref_id,
                         datetime.utcnow().isoformat()))

    def timeline(self, limit: int = 50) -> List[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM growth_log ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def learning_rate(self) -> Dict:
        with self._cur() as cur:
            cur.execute("SELECT COUNT(*) c FROM usage_events")
            total = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM suggestions")
            sugg = cur.fetchone()["c"]
            cur.execute("SELECT COUNT(*) c FROM suggestions WHERE status='applied'")
            applied = cur.fetchone()["c"]
        return {"total_events": total, "suggestions": sugg, "applied": applied,
                "conversion": round(applied / sugg, 2) if sugg else 0.0}


_engine = None

def get_growth_engine(db_path: Optional[str] = None):
    global _engine
    if _engine is None:
        _engine = GrowthEngine(db_path or "./data/growth/growth.db")
    return _engine
