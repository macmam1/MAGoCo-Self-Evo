"""Integrations Registry - lightweight modular version."""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import (
    IntegrationManifest, IntegrationCategory, IntegrationStatus,
    IntegrationSearchQuery, IntegrationSearchResult,
)

logger = logging.getLogger(__name__)


class IntegrationsRegistry:
    def __init__(self, registry_dir: str = "./data/integrations", db_path: str = "./data/integrations/registry.db"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS integrations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                version TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                author TEXT DEFAULT '',
                base_url TEXT DEFAULT '',
                status TEXT DEFAULT 'draft',
                is_public INTEGER DEFAULT 1,
                featured INTEGER DEFAULT 0,
                price REAL DEFAULT 0.0,
                rating REAL DEFAULT 0.0,
                downloads INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                manifest TEXT DEFAULT '{}'
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_int_cat ON integrations(category)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_int_status ON integrations(status)")
        self.conn.commit()

    @contextmanager
    def _cursor(self):
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def create(self, manifest: IntegrationManifest) -> str:
        manifest.updated_at = datetime.utcnow()
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO integrations
                (id,name,display_name,description,version,category,tags,author,base_url,status,is_public,featured,price,rating,downloads,created_at,updated_at,manifest)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    manifest.id, manifest.name, manifest.display_name, manifest.description,
                    manifest.version, manifest.category.value, json.dumps(list(manifest.tags)),
                    manifest.author, manifest.base_url, manifest.status.value,
                    int(manifest.is_public), int(manifest.featured),
                    manifest.price, manifest.rating, manifest.downloads,
                    manifest.created_at.isoformat(), manifest.updated_at.isoformat(),
                    json.dumps(manifest.to_dict()),
                ),
            )
        d = self.registry_dir / manifest.id / manifest.version
        d.mkdir(parents=True, exist_ok=True)
        with open(d / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        return manifest.id

    def get(self, integration_id: str, version: Optional[str] = None) -> Optional[IntegrationManifest]:
        with self._cursor() as cur:
            cur.execute("SELECT manifest FROM integrations WHERE id=? ORDER BY version DESC LIMIT 1", (integration_id,))
            row = cur.fetchone()
            if row and row["manifest"]:
                return IntegrationManifest.from_dict(json.loads(row["manifest"]))
        return None

    def list_all(self, limit: int = 50) -> List[IntegrationManifest]:
        with self._cursor() as cur:
            cur.execute("SELECT manifest FROM integrations ORDER BY updated_at DESC LIMIT ?", (limit,))
            return [IntegrationManifest.from_dict(json.loads(r["manifest"])) for r in cur.fetchall()]

    def search(self, query: IntegrationSearchQuery) -> List[IntegrationSearchResult]:
        conds, params = [], []
        if query.query:
            conds.append("(name LIKE ? OR display_name LIKE ? OR description LIKE ?)")
            params.extend([f"%{query.query}%"] * 3)
        if query.category:
            conds.append("category=?")
            params.append(query.category.value)
        if query.free_only:
            conds.append("price=0")
        if query.featured_only:
            conds.append("featured=1")
        where = f"WHERE {' AND '.join(conds)}" if conds else ""
        order = "ORDER BY rating DESC, downloads DESC"
        limit = f"LIMIT {query.page_size} OFFSET {(query.page-1)*query.page_size}"
        with self._cursor() as cur:
            cur.execute(f"SELECT manifest FROM integrations {where} {order} {limit}", params)
            out = []
            for r in cur.fetchall():
                m = IntegrationManifest.from_dict(json.loads(r["manifest"]))
                out.append(IntegrationSearchResult(integration=m, score=m.rating, matched_fields=[]))
            return out

    def get_stats(self) -> Dict:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) c FROM integrations")
            total = cur.fetchone()["c"]
            cur.execute("SELECT category,COUNT(*) c FROM integrations GROUP BY category")
            by_cat = {r["category"]: r["c"] for r in cur.fetchall()}
        return {"total_integrations": total, "by_category": by_cat}


_registry = None

def get_integrations_registry(registry_dir: Optional[str] = None):
    global _registry
    if _registry is None:
        _registry = IntegrationsRegistry(registry_dir or "./data/integrations")
    return _registry
