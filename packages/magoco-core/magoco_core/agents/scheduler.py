"""Professional scheduler — cron-triggered + background agent tasks.

Why not APScheduler: zero new dependencies, SQLite-durable, single-flight per
schedule, every run recorded (reviewable), global + per-request kill-switches.

- Schedules persist across restarts and reload on start().
- Cron supports: * , */n, ranges (1-5), lists (1,3,5) per field.
- Background one-shots run immediately without blocking the caller.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_field(expr: str, lo: int, hi: int) -> set:
    """Parse one cron field into a set of matching ints."""
    out: set = set()
    for part in expr.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            part, step_s = part.split("/", 1)
            step = max(1, int(step_s))
        if part in ("*", ""):
            out.update(range(lo, hi + 1, step))
        elif "-" in part:
            a, b = part.split("-", 1)
            out.update(range(max(lo, int(a)), min(hi, int(b)) + 1, step))
        else:
            v = int(part)
            if lo <= v <= hi:
                out.add(v)
    return out


def cron_due(cron_expr: str, now: Optional[datetime] = None) -> bool:
    """True if a cron expression fires at `now` (minute precision)."""
    now = now or datetime.utcnow()
    try:
        minute, hour, dom, month, dow = cron_expr.strip().split()
    except ValueError:
        raise ValueError("cron needs 5 fields: 'minute hour dom month dow'")
    # cron dow: 0 and 7 both mean Sunday
    py_dow = (now.weekday() + 1) % 7
    checks = [
        (minute, 0, 59, now.minute),
        (hour, 0, 23, now.hour),
        (dom, 1, 31, now.day),
        (month, 1, 12, now.month),
        (dow.replace("7", "0"), 0, 6, py_dow),
    ]
    return all(now_v in _parse_field(expr, lo, hi) for expr, lo, hi, now_v in checks)


class Scheduler:
    """Durable cron scheduler + background task runner."""

    def __init__(self, db_path: str = "./data/agents/scheduler.db",
                 tick_seconds: float = 30.0):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.tick_seconds = tick_seconds
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS schedules
            (id TEXT PRIMARY KEY, agent_name TEXT, task TEXT,
             cron TEXT, provider_id TEXT DEFAULT '', model TEXT DEFAULT '',
             enabled INTEGER DEFAULT 1, last_run TEXT, run_count INTEGER DEFAULT 0,
             created_at TEXT, updated_at TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS task_runs
            (id TEXT PRIMARY KEY, kind TEXT, ref_id TEXT, agent_name TEXT,
             status TEXT DEFAULT 'running', result TEXT DEFAULT '',
             error TEXT DEFAULT '', created_at TEXT, finished_at TEXT)""")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_runs_ref ON task_runs(ref_id)")
        self.conn.commit()
        self._dispatch: Optional[Callable[..., Coroutine[Any, Any, str]]] = None
        self._loop_task: Optional[asyncio.Task] = None
        self._running = False
        self._in_flight: set = set()

    @contextmanager
    def _cur(self):
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    # ---------- schedules CRUD ----------

    def add_schedule(self, agent_name: str, task: str, cron: str,
                     provider_id: str = "", model: str = "") -> Dict:
        cron_due(cron)  # validates expression now, raises ValueError if bad
        sid = uuid.uuid4().hex[:8]
        now = datetime.utcnow().isoformat()
        with self._cur() as cur:
            cur.execute("INSERT INTO schedules VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, agent_name, task, cron, provider_id, model,
                         1, None, 0, now, now))
        return self.get_schedule(sid)

    def get_schedule(self, sid: str) -> Optional[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM schedules WHERE id=?", (sid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def list_schedules(self, enabled_only: bool = False) -> List[Dict]:
        with self._cur() as cur:
            if enabled_only:
                cur.execute("SELECT * FROM schedules WHERE enabled=1 ORDER BY created_at DESC")
            else:
                cur.execute("SELECT * FROM schedules ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def set_enabled(self, sid: str, enabled: bool) -> bool:
        with self._cur() as cur:
            cur.execute("UPDATE schedules SET enabled=?, updated_at=? WHERE id=?",
                        (int(enabled), datetime.utcnow().isoformat(), sid))
            return cur.rowcount > 0

    def delete_schedule(self, sid: str) -> bool:
        with self._cur() as cur:
            cur.execute("DELETE FROM schedules WHERE id=?", (sid,))
            return cur.rowcount > 0

    # ---------- runs ----------

    def _new_run(self, kind: str, ref_id: str, agent_name: str) -> str:
        rid = uuid.uuid4().hex[:8]
        with self._cur() as cur:
            cur.execute("INSERT INTO task_runs VALUES (?,?,?,?,?,?,?,?)",
                        (rid, kind, ref_id, agent_name, "running", "", "",
                         datetime.utcnow().isoformat(), None))
        return rid

    def _finish_run(self, rid: str, status: str, result: str = "", error: str = "") -> None:
        with self._cur() as cur:
            cur.execute("""UPDATE task_runs SET status=?, result=?, error=?,
                finished_at=? WHERE id=?""",
                (status, result[:4000], error[:1000],
                 datetime.utcnow().isoformat(), rid))

    def get_run(self, rid: str) -> Optional[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM task_runs WHERE id=?", (rid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def list_runs(self, limit: int = 50) -> List[Dict]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM task_runs ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cur.fetchall()]

    # ---------- execution ----------

    def on_dispatch(self, fn: Callable[..., Coroutine[Any, Any, str]]) -> None:
        """Register async fn(agent_name, task, provider_id, model) -> str result."""
        self._dispatch = fn

    async def run_background(self, agent_name: str, task: str,
                             provider_id: str = "", model: str = "") -> str:
        """Start a one-shot background task. Returns run id immediately."""
        rid = self._new_run("background", "", agent_name)
        asyncio.create_task(self._execute(rid, agent_name, task, provider_id, model))
        return rid

    async def _execute(self, rid: str, agent_name: str, task: str,
                       provider_id: str, model: str) -> None:
        try:
            if not self._dispatch:
                raise RuntimeError("no dispatch handler registered")
            result = await self._dispatch(agent_name, task, provider_id, model)
            self._finish_run(rid, "completed", result=str(result))
        except asyncio.CancelledError:
            self._finish_run(rid, "cancelled")
        except Exception as e:
            logger.error(f"[scheduler] run {rid} failed: {e}")
            self._finish_run(rid, "failed", error=str(e))

    async def _tick(self) -> None:
        """Fire due schedules (single-flight each)."""
        now = datetime.utcnow()
        minute_key = now.strftime("%Y-%m-%dT%H:%M")
        for s in self.list_schedules(enabled_only=True):
            key = f"{s['id']}:{minute_key}"
            if key in self._in_flight:
                continue
            try:
                due = cron_due(s["cron"], now)
            except ValueError:
                continue
            if not due:
                continue
            # Once per minute max (durable guard against tick overlap)
            if (s["last_run"] or "")[:16] == minute_key:
                continue
            self._in_flight.add(key)
            rid = self._new_run("scheduled", s["id"], s["agent_name"])
            with self._cur() as cur:
                cur.execute("UPDATE schedules SET last_run=?, run_count=run_count+1 WHERE id=?",
                            (now.isoformat(), s["id"]))
            asyncio.create_task(self._scheduled_run(key, rid, s))

    async def _scheduled_run(self, key: str, rid: str, s: Dict) -> None:
        try:
            await self._execute(rid, s["agent_name"], s["task"],
                                s.get("provider_id") or "", s.get("model") or "")
        finally:
            self._in_flight.discard(key)

    async def start(self) -> None:
        self._running = True
        if self._loop_task and not self._loop_task.done():
            return
        self._loop_task = asyncio.create_task(self._loop())
        logger.info("[scheduler] started")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[scheduler] tick error: {e}")
            await asyncio.sleep(self.tick_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("[scheduler] stopped")


_scheduler: Optional[Scheduler] = None


def get_scheduler(db_path: Optional[str] = None) -> Scheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler(db_path or "./data/agents/scheduler.db")
    return _scheduler
