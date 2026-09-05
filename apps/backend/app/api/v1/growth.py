"""Agent Growth API - usage, patterns, suggestions, timeline, sharing."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.growth import get_growth_engine
from magoco_core.growth.models import UsageEvent

router = APIRouter(prefix="/growth", tags=["growth"])


class RecordRequest(BaseModel):
    agent_id: str = "default"
    action: str = ""
    target: str = ""
    params: Dict[str, Any] = {}
    session_id: Optional[str] = None


class ShareRequest(BaseModel):
    from_agent: str = "default"
    to_agent: str = "default"
    memory_ids: List[str] = []


@router.post("/record")
async def record_usage(req: RecordRequest):
    eng = get_growth_engine()
    ev = UsageEvent(agent_id=req.agent_id, action=req.action, target=req.target,
                    params=req.params, session_id=req.session_id)
    eid = eng.record(ev)
    return {"success": True, "id": eid}


@router.post("/mine")
async def mine_patterns(min_count: int = 3, seq_len: int = 3):
    eng = get_growth_engine()
    patterns = eng.mine_patterns(min_count=min_count, seq_len=seq_len)
    return [p.to_dict() for p in patterns]


@router.post("/suggest")
async def suggest():
    eng = get_growth_engine()
    out = eng.suggest_from_patterns()
    return [s.to_dict() for s in out]


@router.get("/suggestions")
async def list_suggestions(status: Optional[str] = None):
    eng = get_growth_engine()
    return eng.list_suggestions(status=status)


@router.post("/suggestions/{sid}/{action}")
async def suggestion_action(sid: str, action: str):
    eng = get_growth_engine()
    ok = eng.set_suggestion_status(sid, action)
    if action == "approved":
        from magoco_core.growth.models import GrowthEventType
        eng.log(GrowthEventType.SKILL_CREATED, f"suggestion {sid} approved", ref_id=sid)
    return {"success": ok}


@router.post("/suggestions/{sid}/apply")
async def apply_suggestion(sid: str):
    """Approve suggestion AND create a draft skill in Skills Registry."""
    from magoco_core.skills import get_skills_registry
    from magoco_core.skills.models import (
        SkillManifest, SkillCategory, SkillType, SkillStatus,
        SecurityLevel, ExecutionMode,
    )
    eng = get_growth_engine()
    rows = eng.list_suggestions()
    row = next((r for r in rows if r["id"] == sid), None)
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="suggestion not found")
    import json as _json
    draft = _json.loads(row["draft"]) if isinstance(row["draft"], str) else (row["draft"] or {})
    steps = draft.get("steps", [])
    skill_name = (draft.get("name") or f"auto-skill-{sid[:6]}").lower().replace(" ", "-")
    code_lines = ["def main(input_data):", '    """Auto-generated from usage pattern."""', "    log = []"]
    for st in steps:
        code_lines.append(f"    log.append({repr(st)})  # TODO: wire real call")
    code_lines.append('    return {"steps": log}')
    manifest = SkillManifest(
        id=skill_name, name=skill_name,
        display_name=draft.get("name") or skill_name,
        description=f"Auto-generated from pattern (suggestion {sid})",
        version="0.1.0",
        category=SkillCategory.AUTOMATION, type=SkillType.CHAIN,
        tags={"auto-generated", "growth"},
        author="growth-engine",
        entry_point="main", code_path="skill.py",
        execution_mode=ExecutionMode.SYNC,
        security_level=SecurityLevel.RESTRICTED,
        status=SkillStatus.DRAFT,
    )
    reg = get_skills_registry()
    try:
        reg.create(manifest)
    except ValueError:
        pass  # already exists -> treat as idempotent
    # write generated code file
    try:
        from pathlib import Path
        p = reg.registry_dir / manifest.id / manifest.version
        p.mkdir(parents=True, exist_ok=True)
        (p / "skill.py").write_text("\n".join(code_lines), encoding="utf-8")
    except Exception:
        pass
    eng.set_suggestion_status(sid, "applied")
    from magoco_core.growth.models import GrowthEventType
    eng.log(GrowthEventType.SKILL_CREATED, f"draft skill {skill_name} created from {sid}", ref_id=skill_name)
    return {"success": True, "skill_id": skill_name, "version": "0.1.0"}


@router.get("/timeline")
async def timeline(limit: int = 50):
    eng = get_growth_engine()
    return eng.timeline(limit=limit)


@router.get("/learning-rate")
async def learning_rate():
    eng = get_growth_engine()
    return eng.learning_rate()


@router.post("/share")
async def share_memory(req: ShareRequest):
    """Cross-agent memory sharing: copy entries from one agent scope to another."""
    from magoco_core.memory import get_memory_store
    store = get_memory_store()
    shared = 0
    # Simplified: search by agent tag then re-add with new scope tag
    from magoco_core.memory.models import MemoryQuery, MemoryScope
    q = MemoryQuery(query="", scopes=[MemoryScope.USER], top_k=200)
    for r in store.search(q):
        tags = set(r.entry.tags)
        if f"agent:{req.from_agent}" in tags or req.from_agent == "default":
            from magoco_core.memory.models import MemoryEntry, MemoryType
            e = r.entry
            e.id = __import__("uuid").uuid4().hex[:8]
            e.tags = tags | {f"agent:{req.to_agent}", "shared"}
            e.source = "shared"
            store.add(e)
            shared += 1
            if shared >= 50:
                break
    eng = get_growth_engine()
    from magoco_core.growth.models import GrowthEventType
    eng.log(GrowthEventType.MEMORY_CONSOLIDATED, f"shared {shared} memories {req.from_agent}->{req.to_agent}")
    return {"success": True, "shared": shared}
