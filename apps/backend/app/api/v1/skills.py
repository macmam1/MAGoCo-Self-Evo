"""
Skills System API Routes
REST API for skills management, marketplace, execution
"""

from fastapi import APIRouter, HTTPException, Query, Depends, File, UploadFile, Form
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid

from magoco_core.skills import (
    get_skills_registry, get_skill_invoker,
    SkillManifest, SkillCategory, SkillType, SkillStatus,
    SecurityLevel, ExecutionMode, SkillParameter, SkillReturn,
    SkillDependency, SkillTest, SkillExample, SkillReview,
    SkillSearchQuery, SkillSearchResult, SkillComposition,
    SkillParameter, SkillReturn, SkillDependency, SkillTest,
    SkillExample, SkillReview, SkillManifest, SkillCategory,
    SkillType, SkillStatus, SecurityLevel, ExecutionMode
)

router = APIRouter(prefix="/skills", tags=["skills"])


# ============ Request/Response Models ============

class SkillCreateRequest(BaseModel):
    name: str
    display_name: str
    description: str
    version: str = "1.0.0"
    category: str = "custom"
    type: str = "function"
    tags: List[str] = []
    author: str
    author_email: str = ""
    organization: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    entry_point: str = "main"
    code_path: str = "skill.py"
    requirements: List[str] = []
    system_requirements: List[str] = []
    execution_mode: str = "sync"
    timeout: float = 30.0
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    security_level: str = "restricted"
    allowed_domains: List[str] = []
    allowed_commands: List[str] = []
    parameters: List[Dict[str, Any]] = []
    returns: Dict[str, Any] = {"type": "any", "description": ""}
    dependencies: List[Dict[str, Any]] = []
    tests: List[Dict[str, Any]] = []
    examples: List[Dict[str, Any]] = []
    min_core_version: str = "0.3.0"
    compatible_platforms: List[str] = ["linux", "macos", "windows"]
    price: float = 0.0
    currency: str = "USD"
    is_public: bool = True


class SkillUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    price: Optional[float] = None
    is_public: Optional[bool] = None
    featured: Optional[bool] = None


class SkillExecuteRequest(BaseModel):
    skill_id: str
    input_data: Dict[str, Any] = {}
    config: Dict[str, Any] = {}
    secrets: Dict[str, str] = {}
    version: Optional[str] = None
    retries: int = 3


class SkillReviewRequest(BaseModel):
    skill_id: str
    version: str
    rating: int = Field(ge=1, le=5)
    title: str = ""
    content: str = ""


class CompositionCreateRequest(BaseModel):
    name: str
    description: str = ""
    skills: List[str] = []
    connections: List[Dict[str, str]] = []
    parallel_groups: List[List[str]] = []
    conditionals: List[Dict[str, Any]] = []


def get_registry():
    return get_skills_registry()


def get_invoker():
    return get_skill_invoker()


# ============ Skill CRUD ============

@router.post("/", response_model=Dict[str, Any])
async def create_skill(request: SkillCreateRequest):
    """Create a new skill"""
    registry = get_registry()
    
    try:
        # Convert enums
        category = SkillCategory(request.category)
        skill_type = SkillType(request.type)
        execution_mode = ExecutionMode(request.execution_mode)
        security_level = SecurityLevel(request.security_level)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum value: {e}")
    
    # Build manifest
    manifest = SkillManifest(
        id=request.name.lower().replace(" ", "-"),
        name=request.name.lower().replace(" ", "-"),
        display_name=request.display_name,
        description=request.description,
        version=request.version,
        category=category,
        type=skill_type,
        tags=set(request.tags),
        author=request.author,
        author_email=request.author_email,
        organization=request.organization,
        license=request.license,
        homepage=request.homepage,
        repository=request.repository,
        entry_point=request.entry_point,
        code_path=request.code_path,
        requirements=request.requirements,
        system_requirements=request.system_requirements,
        execution_mode=execution_mode,
        timeout=request.timeout,
        max_memory_mb=request.max_memory_mb,
        max_cpu_percent=request.max_cpu_percent,
        security_level=SecurityLevel(request.security_level),
        allowed_domains=request.allowed_domains,
        allowed_commands=request.allowed_commands,
        parameters=[SkillParameter(**p) for p in request.parameters],
        returns=SkillReturn(**request.returns) if request.returns else SkillReturn(type="any"),
        dependencies=[SkillDependency(**d) for d in request.dependencies],
        tests=[SkillTest(**t) for t in request.tests],
        examples=[SkillExample(**e) for e in request.examples],
        min_core_version=request.min_core_version,
        compatible_platforms=request.compatible_platforms,
        price=request.price,
        currency=request.currency,
        is_public=request.is_public,
        status=SkillStatus.DRAFT,
    )
    
    try:
        registry.create(manifest)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {"success": True, "skill_id": manifest.id, "version": manifest.version}


@router.get("/", response_model=List[Dict[str, Any]])
async def list_skills(
    category: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    author: Optional[str] = None,
    featured: Optional[bool] = None,
    free_only: bool = False,
    sort_by: str = "relevance",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    registry=Depends(get_registry),
):
    """List skills with filters"""
    try:
        cat = SkillCategory(category) if category else None
        typ = SkillType(type) if type else None
        stat = SkillStatus(status) if status else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid enum: {e}")
    
    query = SkillSearchQuery(
        category=cat,
        type=typ,
        author=author,
        free_only=free_only,
        featured_only=featured or False,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    
    if stat:
        query.status = stat
    
    results = registry.search(query)
    
    return [
        {
            "skill": r.skill.to_dict(),
            "score": r.score,
            "matched_fields": r.matched_fields,
        }
        for r in results
    ]


@router.get("/featured", response_model=List[Dict[str, Any]])
async def get_featured_skills(limit: int = 10, registry=Depends(get_registry)):
    """Get featured skills"""
    skills = registry.get_featured(limit)
    return [s.to_dict() for s in skills]


@router.get("/popular", response_model=List[Dict[str, Any]])
async def get_popular_skills(limit: int = 10, registry=Depends(get_registry)):
    """Get most popular skills"""
    skills = registry.get_popular(limit)
    return [s.to_dict() for s in skills]


@router.get("/recent", response_model=List[Dict[str, Any]])
async def get_recent_skills(limit: int = 10, registry=Depends(get_registry)):
    """Get recently updated skills"""
    skills = registry.get_recent(limit)
    return [s.to_dict() for s in skills]


@router.get("/categories", response_model=List[str])
async def list_categories():
    """List all skill categories"""
    return [c.value for c in SkillCategory]


@router.get("/types", response_model=List[str])
async def list_types():
    """List all skill types"""
    return [t.value for t in SkillType]


# ===== Curated bank + importer + auto-detection (static routes stay above /{skill_id}) =====

class SkillImportUrlRequest(BaseModel):
    url: str
    category: str = "custom"
    author: str = "imported"


class SkillSuggestRequest(BaseModel):
    text: str = ""
    top_k: int = 5


class SkillSuggestProjectRequest(BaseModel):
    project_type: str = "generic"
    goal: str = ""
    top_k: int = 8


def _suggestion_to_dict(s) -> Dict[str, Any]:
    return {"skill_id": s.skill_id, "display_name": s.display_name,
            "category": s.category, "score": s.score,
            "matched": s.matched, "reason": s.reason}


@router.post("/seed-catalog", response_model=Dict[str, Any])
async def seed_catalog(overwrite: bool = False, registry=Depends(get_registry)):
    """Register the curated BEST-OF bank (idempotent unless overwrite)."""
    from magoco_core.skills.seed_catalog import SEED_CATALOG
    from magoco_core.skills.importer import manifest_from_catalog
    results = {"created": 0, "skipped": 0, "errors": []}
    for entry in SEED_CATALOG:
        try:
            if registry.get(entry["id"]):
                if not overwrite:
                    results["skipped"] += 1
                    continue
                registry.delete(entry["id"], hard=True)
            registry.create(manifest_from_catalog(entry))
            results["created"] += 1
        except Exception as e:
            results["errors"].append(f"{entry['id']}: {str(e)[:200]}")
    results["total"] = len(SEED_CATALOG)
    return results


@router.post("/import-url", response_model=Dict[str, Any])
async def import_skill_url(req: SkillImportUrlRequest, registry=Depends(get_registry)):
    """Fetch any SKILL.md by URL (github blob auto-converted), validate, register as DRAFT."""
    from magoco_core.skills.importer import import_from_url
    try:
        manifest = await import_from_url(req.url, category=req.category, author=req.author)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fetch failed: {str(e)[:300]}")
    try:
        sid = registry.create(manifest)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)[:300])
    return {"success": True, "skill_id": sid, "version": manifest.version}


@router.post("/suggest", response_model=List[Dict[str, Any]])
async def suggest_skills(req: SkillSuggestRequest, registry=Depends(get_registry)):
    """Auto-detect skills for free text (task/message/goal). Deterministic scoring."""
    from magoco_core.skills.detect import suggest_for_text
    return [_suggestion_to_dict(s) for s in suggest_for_text(req.text, req.top_k, registry)]


@router.post("/suggest-for-project", response_model=List[Dict[str, Any]])
async def suggest_skills_for_project(req: SkillSuggestProjectRequest,
                                     registry=Depends(get_registry)):
    """Skills to pre-activate when a project of this type starts."""
    from magoco_core.skills.detect import suggest_for_project
    return [_suggestion_to_dict(s) for s in suggest_for_project(
        req.project_type, req.goal, req.top_k, registry)]


@router.get("/{skill_id}", response_model=Dict[str, Any])
async def get_skill(skill_id: str, version: Optional[str] = None, registry=Depends(get_registry)):
    """Get a skill by ID"""
    skill = registry.get(skill_id, version)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@router.get("/{skill_id}/versions", response_model=List[str])
async def list_versions(skill_id: str, registry=Depends(get_registry)):
    """List all versions of a skill"""
    return registry.list_versions(skill_id)


@router.patch("/{skill_id}/{version}", response_model=Dict[str, Any])
async def update_skill(skill_id: str, version: str, request: SkillUpdateRequest, registry=Depends(get_registry)):
    """Update a skill (draft only)"""
    skill = registry.get(skill_id, version)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    if skill.status != SkillStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Can only update draft skills")
    
    # Apply updates
    if request.display_name:
        skill.display_name = request.display_name
    if request.description is not None:
        skill.description = request.description
    if request.category:
        skill.category = SkillCategory(request.category)
    if request.tags is not None:
        skill.tags = set(request.tags)
    if request.requirements is not None:
        skill.requirements = request.requirements
    if request.parameters is not None:
        skill.parameters = [SkillParameter(**p) for p in request.parameters]
    if request.price is not None:
        skill.price = request.price
    if request.is_public is not None:
        skill.is_public = request.is_public
    if request.featured is not None:
        skill.featured = request.featured
    
    skill.updated_at = datetime.utcnow()
    registry.update(skill)
    
    return {"success": True, "skill": skill.to_dict()}


@router.post("/{skill_id}/{version}/publish", response_model=Dict[str, Any])
async def publish_skill(skill_id: str, version: str, registry=Depends(get_registry)):
    """Publish a skill (draft -> published)"""
    success = registry.publish(skill_id, version)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to publish skill")
    return {"success": True, "message": "Skill published"}


@router.post("/{skill_id}/{version}/deprecate", response_model=Dict[str, Any])
async def deprecate_skill(skill_id: str, version: str, registry=Depends(get_registry)):
    """Deprecate a skill"""
    skill = registry.get(skill_id, version)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    skill.status = SkillStatus.DEPRECATED
    skill.updated_at = datetime.utcnow()
    registry.update(skill)
    
    return {"success": True, "message": "Skill deprecated"}


@router.delete("/{skill_id}/{version}", response_model=Dict[str, Any])
async def delete_skill(skill_id: str, version: str, hard: bool = False, registry=Depends(get_registry)):
    """Delete a skill version"""
    skill = registry.get(skill_id, version)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    registry.delete(skill_id, version, hard=hard)
    return {"success": True}


# ============ Skill Execution ============

@router.post("/execute", response_model=Dict[str, Any])
async def execute_skill(request: SkillExecuteRequest, invoker=Depends(get_invoker)):
    """Execute a skill"""
    result = await invoker.invoke(
        skill_id=request.skill_id,
        input_data=request.input_data,
        config=request.config,
        secrets=request.secrets,
        version=request.version,
        retries=request.retries,
    )
    
    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "execution_time": result.execution_time,
        "metadata": result.metadata,
    }


@router.post("/execute/stream")
async def execute_skill_stream(request: SkillExecuteRequest, invoker=Depends(get_invoker)):
    """Execute a skill with streaming output"""
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate():
        async for chunk in invoker.invoke_streaming(
            skill_id=request.skill_id,
            input_data=request.input_data,
            config=request.config,
            secrets=request.secrets,
            version=request.version,
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


# ============ Skill Validation & Testing ============

@router.post("/{skill_id}/{version}/validate", response_model=Dict[str, Any])
async def validate_skill(skill_id: str, version: str, registry=Depends(get_registry)):
    """Validate a skill"""
    result = registry.validate_skill(skill_id, version)
    return result


@router.post("/{skill_id}/{version}/test", response_model=Dict[str, Any])
async def run_tests(skill_id: str, version: str, registry=Depends(get_registry)):
    """Run skill tests"""
    result = registry.run_tests(skill_id, version)
    return result


@router.post("/{skill_id}/{version}/check-compatibility", response_model=Dict[str, Any])
async def check_compatibility(
    skill_id: str, version: str, core_version: str = "0.3.0", registry=Depends(get_registry)
):
    """Check skill compatibility with core version"""
    compatible = registry.check_compatibility(skill_id, version, core_version)
    return {"compatible": compatible, "core_version": core_version}


# ============ Reviews & Ratings ============

class ReviewCreateRequest(BaseModel):
    skill_id: str
    version: str
    rating: int = Field(ge=1, le=5)
    title: str = ""
    content: str = ""


@router.post("/{skill_id}/{version}/reviews", response_model=Dict[str, Any])
async def add_review(skill_id: str, version: str, request: ReviewCreateRequest, registry=Depends(get_registry)):
    """Add a review for a skill"""
    # Verify skill exists
    skill = registry.get(skill_id, version)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    review = SkillReview(
        skill_id=skill_id,
        version=version,
        user_id="anonymous",  # In production, get from auth
        rating=request.rating,
        title=request.title,
        content=request.content,
    )
    
    registry.add_review(review)
    return {"success": True, "review_id": review.id}


@router.get("/{skill_id}/reviews", response_model=List[Dict[str, Any]])
async def get_reviews(skill_id: str, version: Optional[str] = None, limit: int = 20, registry=Depends(get_registry)):
    """Get reviews for a skill"""
    reviews = registry.get_reviews(skill_id, version, limit)
    return [r.to_dict() for r in reviews]


# ============ Skill Composition ============

@router.post("/compositions", response_model=Dict[str, Any])
async def create_composition(request: CompositionCreateRequest, registry=Depends(get_registry)):
    """Create a skill composition"""
    composition = SkillComposition(
        name=request.name,
        description=request.description,
        skills=request.skills,
        connections=request.connections,
        parallel_groups=request.parallel_groups,
        conditionals=request.conditionals,
    )
    
    comp_id = registry.create_composition(composition)
    return {"success": True, "composition_id": comp_id}


@router.get("/compositions/{composition_id}", response_model=Dict[str, Any])
async def get_composition(composition_id: str, registry=Depends(get_registry)):
    """Get a skill composition"""
    comp = registry.get_composition(composition_id)
    if not comp:
        raise HTTPException(status_code=404, detail="Composition not found")
    return {
        "id": comp.id,
        "name": comp.name,
        "description": comp.description,
        "skills": comp.skills,
        "connections": comp.connections,
        "parallel_groups": comp.parallel_groups,
        "conditionals": comp.conditionals,
        "version": comp.version,
        "created_at": comp.created_at.isoformat(),
        "updated_at": comp.updated_at.isoformat(),
    }


# ============ Analytics ============

@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_skills_stats(registry=Depends(get_registry)):
    """Get skills registry statistics"""
    return registry.get_stats()


@router.get("/{skill_id}/analytics", response_model=Dict[str, Any])
async def get_skill_analytics(skill_id: str, version: Optional[str] = None, registry=Depends(get_registry)):
    """Get skill analytics"""
    skill = registry.get(skill_id, version)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return {
        "skill_id": skill_id,
        "analytics": skill.analytics.to_dict() if hasattr(skill.analytics, 'to_dict') else skill.analytics.__dict__,
    }


# ============ Skill Upload ============

@router.post("/upload", response_model=Dict[str, Any])
async def upload_skill(
    manifest_file: UploadFile = File(...),
    code_file: UploadFile = File(...),
    requirements_file: Optional[UploadFile] = File(None),
    registry=Depends(get_registry),
):
    """Upload a skill package (manifest + code)"""
    # Read manifest
    manifest_content = await manifest_file.read()
    manifest_data = json.loads(manifest_content)
    
    # Create skill directory
    skill_id = manifest_data.get("id", manifest_data.get("name", "").lower().replace(" ", "-"))
    version = manifest_data.get("version", "1.0.0")
    
    skill_dir = registry.registry_dir / skill_id / version
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    # Save manifest
    manifest_path = skill_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    
    # Save code
    code_content = await code_file.read()
    code_path = skill_dir / manifest_data.get("code_path", "skill.py")
    code_path.parent.mkdir(parents=True, exist_ok=True)
    with open(code_path, "wb") as f:
        f.write(await code_file.read())
    
    # Save requirements if provided
    if requirements_file:
        req_content = await requirements_file.read()
        req_path = skill_dir / "requirements.txt"
        with open(req_path, "wb") as f:
            f.write(req_content)
    
    return {"success": True, "skill_id": skill_id, "version": version, "message": "Skill uploaded successfully"}


# ============ Skill Templates ============

@router.get("/templates", response_model=List[Dict[str, Any]])
async def list_templates(category: Optional[str] = None):
    """List skill templates for quick start"""
    templates = [
        {
            "id": "http-api-wrapper",
            "name": "HTTP API Wrapper",
            "description": "Wrap any HTTP API as a skill",
            "category": "api_integration",
            "code_template": '''async def main(input_data):
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(input_data["url"])
        return response.json()
''',
        },
        {
            "id": "data-transformer",
            "name": "Data Transformer",
            "description": "Transform data with Python expressions",
            "category": "data_processing",
            "code_template": '''def main(input_data):
    data = input_data.get("data", [])
    transform = input_data.get("transform", "x * 2")
    return [eval(transform, {"x": x}) for x in data]
''',
        },
        {
            "id": "file-processor",
            "name": "File Processor",
            "description": "Process files with custom logic",
            "category": "file_operations",
            "code_template": '''def main(input_data):
    import os
    path = input_data["path"]
    with open(path, "r") as f:
        content = f.read()
    # Process content
    return {"processed": len(content)}
''',
        },
    ]
    
    if category:
        templates = [t for t in templates if t["category"] == category]
    
    return templates