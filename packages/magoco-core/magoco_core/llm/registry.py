"""Provider registry — SQLite CRUD, encrypted keys, fetch/test, Ollama autodetect."""

import json
import logging
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from magoco_core.llm.providers import (
    ProviderConfig, ProviderKind, CompatibleProvider, fetch_models, detect_ollama,
)
from magoco_core.llm.vault import encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self, db_path: str = "./data/providers/registry.db", data_dir: str = "./data"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.data_dir = data_dir
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cur = self.conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS providers
            (id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
             base_url TEXT DEFAULT '', api_key_encrypted TEXT DEFAULT '',
             models TEXT DEFAULT '[]', default_model TEXT DEFAULT '',
             enabled INTEGER DEFAULT 1, timeout REAL DEFAULT 120.0,
             extra_headers TEXT DEFAULT '{}',
             created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""")
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

    # ---------- CRUD ----------

    def create(self, name: str, kind: str, base_url: str = "", api_key: str = "",
               models: Optional[List[str]] = None, default_model: str = "",
               enabled: bool = True, timeout: float = 120.0,
               extra_headers: Optional[Dict[str, str]] = None) -> ProviderConfig:
        pid = name.lower().strip().replace(" ", "-") or uuid.uuid4().hex[:8]
        cfg = ProviderConfig(
            id=pid, name=name, kind=ProviderKind(kind),
            base_url=base_url.rstrip("/"),
            api_key_encrypted=encrypt_secret(api_key, self.data_dir),
            models=models or [], default_model=default_model or (models[0] if models else ""),
            enabled=enabled, timeout=timeout, extra_headers=extra_headers or {},
        )
        with self._cur() as cur:
            cur.execute("INSERT OR REPLACE INTO providers VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                cfg.id, cfg.name, cfg.kind.value, cfg.base_url, cfg.api_key_encrypted,
                json.dumps(cfg.models), cfg.default_model, int(cfg.enabled), cfg.timeout,
                json.dumps(cfg.extra_headers),
                cfg.created_at.isoformat(), cfg.updated_at.isoformat(),
            ))
        return cfg

    def get(self, provider_id: str) -> Optional[ProviderConfig]:
        with self._cur() as cur:
            cur.execute("SELECT * FROM providers WHERE id=?", (provider_id,))
            row = cur.fetchone()
            return self._row_to_config(row) if row else None

    def list(self, enabled_only: bool = False) -> List[ProviderConfig]:
        with self._cur() as cur:
            if enabled_only:
                cur.execute("SELECT * FROM providers WHERE enabled=1 ORDER BY updated_at DESC")
            else:
                cur.execute("SELECT * FROM providers ORDER BY updated_at DESC")
            return [self._row_to_config(r) for r in cur.fetchall()]

    def update(self, provider_id: str, **fields) -> Optional[ProviderConfig]:
        cfg = self.get(provider_id)
        if not cfg:
            return None
        if "api_key" in fields:
            cfg.api_key_encrypted = encrypt_secret(fields.pop("api_key") or "", self.data_dir)
        for k in ("name", "base_url", "models", "default_model", "enabled",
                  "timeout", "extra_headers"):
            if k in fields and fields[k] is not None:
                setattr(cfg, k, fields[k])
        if "kind" in fields and fields["kind"]:
            cfg.kind = ProviderKind(fields["kind"])
        cfg.updated_at = datetime.utcnow()
        with self._cur() as cur:
            cur.execute("""UPDATE providers SET name=?,kind=?,base_url=?,api_key_encrypted=?,
                models=?,default_model=?,enabled=?,timeout=?,extra_headers=?,updated_at=? WHERE id=?""", (
                cfg.name, cfg.kind.value, cfg.base_url, cfg.api_key_encrypted,
                json.dumps(cfg.models), cfg.default_model, int(cfg.enabled), cfg.timeout,
                json.dumps(cfg.extra_headers), cfg.updated_at.isoformat(), cfg.id,
            ))
        return cfg

    def delete(self, provider_id: str) -> bool:
        with self._cur() as cur:
            cur.execute("DELETE FROM providers WHERE id=?", (provider_id,))
            return cur.rowcount > 0

    def _row_to_config(self, row: sqlite3.Row) -> ProviderConfig:
        d = dict(row)
        d["models"] = json.loads(d["models"] or "[]")
        d["extra_headers"] = json.loads(d["extra_headers"] or "{}")
        d["enabled"] = bool(d["enabled"])
        return ProviderConfig.from_dict(d)

    # ---------- runtime helpers ----------

    def decrypt_key(self, cfg: ProviderConfig) -> str:
        return decrypt_secret(cfg.api_key_encrypted, self.data_dir)

    def to_runtime(self, cfg: ProviderConfig) -> CompatibleProvider:
        """Build a live provider client from stored config."""
        return CompatibleProvider(
            base_url=cfg.base_url, api_key=self.decrypt_key(cfg),
            name=f"{cfg.id}", models=cfg.models,
            timeout=cfg.timeout, extra_headers=cfg.extra_headers,
        )

    async def fetch_and_save_models(self, provider_id: str) -> List[str]:
        cfg = self.get(provider_id)
        if not cfg:
            raise ValueError("provider not found")
        models = await fetch_models(cfg.base_url, self.decrypt_key(cfg), cfg.extra_headers, timeout=10.0)
        self.update(provider_id, models=models,
                    default_model=cfg.default_model or (models[0] if models else ""))
        return models

    async def test_connection(self, provider_id: str) -> Dict:
        """Try GET /models; report ok + model count or the exact error."""
        cfg = self.get(provider_id)
        if not cfg:
            return {"ok": False, "error": "provider not found"}
        try:
            models = await fetch_models(cfg.base_url, self.decrypt_key(cfg), cfg.extra_headers, timeout=10.0)
            return {"ok": True, "models": len(models), "sample": models[:5]}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}

    async def autodetect_ollama(self) -> Optional[ProviderConfig]:
        """If a reachable Ollama exists and no ollama provider stored, create it."""
        with self._cur() as cur:
            cur.execute("SELECT id FROM providers WHERE kind='ollama-local' LIMIT 1")
            if cur.fetchone():
                return None
        base = await detect_ollama()
        if not base:
            return None
        cfg = self.create(name="Ollama (local)", kind="ollama-local", base_url=base)
        try:
            await self.fetch_and_save_models(cfg.id)
        except Exception as e:
            logger.warning("ollama fetch failed: %s", e)
        return self.get(cfg.id)


_registry = None

def get_provider_registry(db_path: Optional[str] = None, data_dir: Optional[str] = None):
    global _registry
    if _registry is None:
        _registry = ProviderRegistry(db_path or "./data/providers/registry.db", data_dir or "./data")
    return _registry
