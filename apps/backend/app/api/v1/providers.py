"""Providers API - BYOM: user adds Ollama-local or OpenAI-compatible endpoints."""

from datetime import datetime
from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.llm.registry import get_provider_registry

router = APIRouter(prefix="/providers", tags=["providers"])


class ProviderCreate(BaseModel):
    name: str
    kind: str = "openai-compatible"  # ollama-local | openai-compatible
    base_url: str = ""
    api_key: str = ""
    models: List[str] = []
    default_model: str = ""
    enabled: bool = True
    timeout: float = 120.0
    extra_headers: Dict[str, str] = {}


class ProviderUpdate(BaseModel):
    name: Optional[str] = None
    kind: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    models: Optional[List[str]] = None
    default_model: Optional[str] = None
    enabled: Optional[bool] = None
    timeout: Optional[float] = None
    extra_headers: Optional[Dict[str, str]] = None


class ProviderImport(BaseModel):
    """Bulk import providers from JSON."""
    providers: List[ProviderCreate]
    overwrite: bool = False  # if true, delete existing providers with same ID


def _public(cfg) -> Dict[str, Any]:
    d = cfg.to_dict()
    d.pop("api_key_encrypted", None)  # NEVER leak ciphertext to clients
    return d


def _exportable(cfg) -> Dict[str, Any]:
    """Exportable format including encrypted key for backup/migration."""
    d = cfg.to_dict(include_secret=True)
    return d


@router.get("/")
async def list_providers(enabled_only: bool = False):
    reg = get_provider_registry()
    return [_public(c) for c in reg.list(enabled_only=enabled_only)]


@router.post("/")
async def create_provider(req: ProviderCreate):
    reg = get_provider_registry()
    if req.kind not in ("ollama-local", "openai-compatible"):
        raise HTTPException(status_code=400, detail="kind must be ollama-local|openai-compatible")
    if not req.base_url:
        raise HTTPException(status_code=400, detail="base_url required")
    cfg = reg.create(req.name, req.kind, req.base_url, req.api_key, req.models,
                     req.default_model, req.enabled, req.timeout, req.extra_headers)
    return _public(cfg)


# NOTE: static routes must stay ABOVE /{provider_id} (FastAPI matches in order).

@router.post("/autodetect-ollama")
async def autodetect_ollama():
    reg = get_provider_registry()
    cfg = await reg.autodetect_ollama()
    if not cfg:
        return {"success": False, "message": "no reachable Ollama, or already configured"}
    return {"success": True, "provider": _public(cfg)}


# ===== Import/Export Endpoints =====

@router.get("/export")
async def export_providers(include_secrets: bool = False):
    """Export all providers as JSON (for backup/migration)."""
    reg = get_provider_registry()
    providers = reg.list(enabled_only=False)
    if include_secrets:
        data = [_exportable(c) for c in providers]
    else:
        data = [_public(c) for c in providers]
    return {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "count": len(data),
        "providers": data
    }


@router.post("/import")
async def import_providers(req: ProviderImport):
    """Bulk import providers from JSON."""
    reg = get_provider_registry()
    results = {"created": 0, "updated": 0, "skipped": 0, "errors": []}

    for p in req.providers:
        try:
            # Check if provider with same ID exists
            existing = reg.get(p.name.lower().strip().replace(" ", "-") or "")
            if existing:
                if req.overwrite:
                    reg.delete(existing.id)
                    cfg = reg.create(p.name, p.kind, p.base_url, p.api_key, p.models,
                                     p.default_model, p.enabled, p.timeout, p.extra_headers)
                    results["updated"] += 1
                else:
                    results["skipped"] += 1
                    results["errors"].append(f"Provider '{p.name}' already exists (use overwrite=true)")
                    continue
            else:
                cfg = reg.create(p.name, p.kind, p.base_url, p.api_key, p.models,
                                 p.default_model, p.enabled, p.timeout, p.extra_headers)
                results["created"] += 1
        except Exception as e:
            results["errors"].append(f"{p.name}: {str(e)}")

    return results


@router.post("/import-file")
async def import_providers_file(file: UploadFile = File(...), overwrite: bool = False):
    """Import providers from uploaded JSON file."""
    import json
    content = await file.read()
    try:
        data = json.loads(content)
        providers = data.get("providers", [])
        req = ProviderImport(providers=providers, overwrite=overwrite)
        return await import_providers(req)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")


# ===== Gateway observability (read-only) =====

@router.get("/gateway/status")
async def gateway_status():
    """Costs + rate limits + available models (read-only monitoring)."""
    from magoco_core.llm.gateway import llm_gateway
    return {
        "providers": list(llm_gateway.providers.keys()),
        "preferred_order": llm_gateway.preferred_order,
        "costs": llm_gateway.get_current_costs(),
        "rate_limits": {name: llm_gateway.get_rate_limit_status(name)
                        for name in llm_gateway.providers.keys()},
        "models": llm_gateway.get_available_models(),
    }


@router.get("/gateway/fallbacks")
async def gateway_fallbacks(limit: int = 20):
    """Recent fallback chains (which provider failed, where it landed, latency)."""
    from magoco_core.llm.gateway import llm_gateway
    return llm_gateway.get_fallback_chains(limit)


@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    reg = get_provider_registry()
    cfg = reg.get(provider_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="not found")
    return _public(cfg)


@router.patch("/{provider_id}")
async def update_provider(provider_id: str, req: ProviderUpdate):
    reg = get_provider_registry()
    cfg = reg.update(provider_id, **{k: v for k, v in req.model_dump().items() if v is not None})
    if not cfg:
        raise HTTPException(status_code=404, detail="not found")
    return _public(cfg)


@router.delete("/{provider_id}")
async def delete_provider(provider_id: str):
    reg = get_provider_registry()
    if not reg.delete(provider_id):
        raise HTTPException(status_code=404, detail="not found")
    return {"success": True}


@router.post("/{provider_id}/fetch-models")
async def fetch_models_endpoint(provider_id: str):
    reg = get_provider_registry()
    try:
        models = await reg.fetch_and_save_models(provider_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fetch failed: {str(e)[:300]}")
    return {"success": True, "models": models}


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str):
    reg = get_provider_registry()
    result = await reg.test_connection(provider_id)
    if not result.get("ok") and result.get("error") == "provider not found":
        raise HTTPException(status_code=404, detail="not found")
    return result



