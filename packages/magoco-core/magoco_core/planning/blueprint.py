"""Project Blueprint — atoms.dev-style full-stack multi-track planning, done professionally.

Given a project goal, generates a validated multi-track plan:
  Phase 0 (parallel): Research + Spec
  Phase 1: Architecture (system blueprint + API contracts + DB schema)
  Phase 2 (parallel tracks): frontend / backend / database / auth / tests / docs...
  Phase 3: Integration (wire tracks against the contracts)
  Phase 4: Verify (review + tests vs definitions-of-done)
  Phase 5: Ship (synthesis + human approval gate)

Better than atoms.dev's black box:
- Every track declares a cross-track CONTRACT first (API shapes, DB tables);
  integration tasks depend on contracts, not vibes.
- Every task has a definition_of_done (Atom oracle lesson).
- The whole blueprint validates (acyclic, known deps) before commit.
- Tracks are data (STACK_TRACKS), not hardcoded branches — new project types
  plug in without code changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing Any, Dict, List, Optional

from magoco_core.planning import Plan, PlanLayer, PlanTask


@dataclass
class StackTrack:
    """One parallel workstream of a real project."""
    key: str                    # e.g. frontend
    title: str                  # e.g. "Frontend"
    agent_role: str             # specialist owner
    tool_requirements: List[str] = field(default_factory=list)
    deliverable: str = ""       # what this track produces
    definition_of_done: str = ""
    contract_needs: List[str] = field(default_factory=list)  # contracts it consumes


# Track catalog per project type. Extend without code changes to the engine.
STACK_TRACKS: Dict[str, List[StackTrack]] = {
    "web_app": [
        StackTrack("frontend", "Frontend", "coder", ["file_write"],
                   "UI pages + flows", "Pages render without console errors; flows clickable end-to-end"),
        StackTrack("backend", "Backend", "coder", ["file_write", "python_exec"],
                   "API endpoints", "Every endpoint in the contract responds 2xx to happy-path calls"),
        StackTrack("database", "Database", "architect", [],
                   "Schema + migrations", "Tables/collections match the contract; migrations apply cleanly"),
        StackTrack("auth", "Auth", "coder", ["file_write"],
                   "Login/session", "Login → session → protected route works"),
        StackTrack("tests", "Tests", "reviewer", ["python_exec", "file_read"],
                   "Test suite", "Suite runs green; failures listed explicitly"),
        StackTrack("docs", "Docs", "researcher", [],
                   "README + setup guide", "A newcomer can run the project from docs alone"),
    ],
    "game": [
        StackTrack("gameplay", "Gameplay", "coder", ["file_write"],
                   "Core loop + mechanics", "Loop playable start-to-finish without crashes"),
        StackTrack("assets", "Assets", "researcher", [],
                   "Sprites/audio/levels list", "Every referenced asset exists or has a placeholder"),
        StackTrack("ui", "Game UI", "coder", ["file_write"],
                   "Menus + HUD", "Menus navigable; HUD shows live state"),
        StackTrack("persistence", "Persistence", "architect", [],
                   "Save/load + scores", "Save → reload restores exact state"),
        StackTrack("tests", "Tests", "reviewer", ["python_exec", "file_read"],
                   "Playtest checklist", "Checklist executed; bugs listed explicitly"),
        StackTrack("docs", "Docs", "researcher", [],
                   "How-to-play + build guide", "A newcomer can build and play from docs"),
    ],
    "saas": [
        StackTrack("frontend", "Frontend", "coder", ["file_write"],
                   "Marketing + app UI", "Signup → dashboard flow works end-to-end"),
        StackTrack("backend", "Backend", "coder", ["file_write", "python_exec"],
                   "API + billing webhooks", "Endpoints + Stripe webhook verified with test events"),
        StackTrack("database", "Database", "architect", [],
                   "Multi-tenant schema", "Tenant isolation verified by query test"),
        StackTrack("auth", "Auth", "coder", ["file_write"],
                   "SSO/session + roles", "Role matrix enforced on every route"),
        StackTrack("growth", "Growth", "researcher", ["web_search"],
                   "SEO + onboarding", "SEO checklist done; onboarding funnel defined"),
        StackTrack("tests", "Tests", "reviewer", ["python_exec", "file_read"],
                   "Test suite", "Suite runs green; failures listed explicitly"),
        StackTrack("docs", "Docs", "researcher", [],
                   "Docs + changelog", "Docs match shipped behavior"),
    ],
    "api_service": [
        StackTrack("spec", "API Spec", "architect", [],
                   "OpenAPI contract", "Spec validates; examples for every endpoint"),
        StackTrack("backend", "Backend", "coder", ["file_write", "python_exec"],
                   "Endpoints", "Contract tests pass against implementation"),
        StackTrack("database", "Database", "architect", [],
                   "Schema", "Migrations apply cleanly; constraints enforced"),
        StackTrack("tests", "Tests", "reviewer", ["python_exec", "file_read"],
                   "Contract + load tests", "All contract tests green"),
        StackTrack("docs", "Docs", "researcher", [],
                   "API reference", "Every endpoint documented with example"),
    ],
}

GENERIC_TRACKS = [
    StackTrack("design", "Design", "architect", [],
               "Approach + structure", "Deliverables listed with owners"),
    StackTrack("build", "Build", "coder", ["file_write"],
               "Implementation", "Works end-to-end per the spec"),
    StackTrack("tests", "Tests", "reviewer", ["file_read"],
               "Verification", "Results checked against definition of done"),
]


def detect_project_type(goal: str) -> str:
    """Cheap heuristic routing to a track catalog."""
    g = (goal or "").lower()
    if any(w in g for w in ("game", "بازی", "play", "level", "sprite")):
        return "game"
    if any(w in g for w in ("saas", "billing", "stripe", "subscription", "tenant")):
        return "saas"
    if any(w in g for w in ("api", "endpoint", "rest", "webhook", "sdk")) and "web" not in g:
        return "api_service"
    if any(w in g for w in ("web", "site", "app", "dashboard", "landing", "وب", "سایت")):
        return "web_app"
    return "generic"


def build_blueprint(goal: str, project_type: str = "auto",
                    layer: PlanLayer = PlanLayer.PROJECT,
                    project_id: Optional[str] = None) -> Plan:
    """Build a validated full-stack multi-track plan for a project goal."""
    ptype = detect_project_type(goal) if project_type == "auto" else project_type
    tracks = STACK_TRACKS.get(ptype, GENERIC_TRACKS)

    import uuid
    plan = Plan(name=f"Blueprint: {goal[:60]}", description=goal,
                layer=layer, project_id=project_id or f"proj-{uuid.uuid4().hex[:6]}")
    plan.metadata["project_type"] = ptype
    plan.metadata["blueprint"] = True

    # Phase 0 (parallel): research + spec
    research = PlanTask(
        name="Research", description=f"Market/tech research for: {goal}",
        agent_role="researcher", tool_requirements=["web_search"],
        definition_of_done="Comparable approaches + key risks listed with sources")
    spec = PlanTask(
        name="Spec", description=f"Scope + user stories + non-goals for: {goal}",
        agent_role="coordinator", tool_requirements=[],
        definition_of_done="Scope, 3-7 user stories, and explicit non-goals written")
    plan.add_task(research)
    plan.add_task(spec)

    # Phase 1: architecture + contracts (depends on both)
    arch = PlanTask(
        name="Architecture & Contracts",
        description=(f"System blueprint for {ptype}: module boundaries, "
                     f"API contracts, DB schema. Tracks: {', '.join(t.title for t in tracks)}"),
        agent_role="architect", tool_requirements=[],
        dependencies=[research.id, spec.id],
        definition_of_done="Contracts written: API shapes + DB tables that tracks will build against")
    plan.add_task(arch)

    # Phase 2: parallel tracks (all depend on architecture)
    track_tasks: List[PlanTask] = []
    for tr in tracks:
        t = PlanTask(
            name=tr.title, description=f"{tr.title} for '{goal}'. Deliverable: {tr.deliverable}",
            agent_role=tr.agent_role, tool_requirements=tr.tool_requirements,
            dependencies=[arch.id],
            definition_of_done=tr.definition_of_done,
            metadata={"track": tr.key, "deliverable": tr.deliverable},
        )
        plan.add_task(t)
        track_tasks.append(t)

    # Phase 3: integration (depends on ALL tracks)
    integrate = PlanTask(
        name="Integration",
        description=f"Wire all tracks against the contracts: {', '.join(t.title for t in tracks)}",
        agent_role="coder", tool_requirements=["file_write", "python_exec", "file_read"],
        dependencies=[t.id for t in track_tasks],
        definition_of_done="Tracks wired together; contract violations listed (none = pass)")
    plan.add_task(integrate)

    # Phase 4: verify
    verify = PlanTask(
        name="Verify",
        description="Review + tests against every track's definition of done",
        agent_role="reviewer", tool_requirements=["file_read", "python_exec"],
        dependencies=[integrate.id],
        definition_of_done="All DoDs checked; remaining gaps listed explicitly")
    plan.add_task(verify)

    # Phase 5: ship (human approval gate lives here — orchestrator pauses via HITL)
    ship = PlanTask(
        name="Ship",
        description="Final synthesis + HUMAN APPROVAL before release",
        agent_role="coordinator", tool_requirements=[],
        dependencies=[verify.id],
        definition_of_done="Human approved; release notes written")
    plan.add_task(ship)

    errors = plan.validate()
    if errors:
        raise ValueError(f"Blueprint invalid: {errors[0]}")
    return plan
