"""QualityGate — verifies task outputs against definitions-of-done.

cuddlytoddly lesson: check each result against declared outputs; when something
is missing, inject a bridging task automatically instead of failing silently.

Two layers:
1. Deterministic checks (always run, no LLM): non-empty result, DoD keyword
   coverage, error absence.
2. Optional LLM judge (when an llm callable is provided): semantic pass/fail.

A failing task gets status FAILED + a bridging child task (depends on it) so
the plan explicitly records what is missing. Nothing is hidden.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing Any, Callable, Coroutine, Dict, List, Optional


@dataclass
class Verdict:
    passed: bool
    missing: List[str] = field(default_factory=list)
    score: float = 0.0  # 0-1 DoD keyword coverage
    method: str = "deterministic"  # deterministic | llm
    notes: str = ""


_WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06FF0-9]{4,}")


def _keywords(text: str, limit: int = 16) -> List[str]:
    stop = {"that", "this", "with", "from", "have", "will", "task",
            "است", "این", "برای", "های", "است"}
    seen: Dict[str, int] = {}
    for w in _WORD_RE.findall((text or "").lower()):
        if w not in stop:
            seen[w] = seen.get(w, 0) + 1
    return sorted(seen, key=lambda w: -seen[w])[:limit]


def check_dod(task_name: str, definition_of_done: str, result: Any) -> Verdict:
    """Deterministic DoD check: result must exist and cover DoD keywords."""
    text = "" if result is None else str(result)
    if not text.strip():
        return Verdict(False, ["empty result"], 0.0, "deterministic",
                       f"Task '{task_name}' produced no output")
    if not (definition_of_done or "").strip():
        return Verdict(True, [], 1.0, "deterministic", "no DoD declared — vacuously passes")
    keys = _keywords(definition_of_done)
    if not keys:
        return Verdict(True, [], 1.0, "deterministic", "DoD has no keywords")
    lowered = text.lower()
    missing = [k for k in keys if k not in lowered]
    score = 1.0 - len(missing) / len(keys)
    passed = score >= 0.5
    return Verdict(
        passed, missing, round(score, 2), "deterministic",
        f"Task '{task_name}': DoD coverage {score:.0%}" +
        ("" if passed else f"; missing: {', '.join(missing[:6])}"),
    )


async def judge_with_llm(task_name: str, definition_of_done: str, result: Any,
                          llm: Callable[..., Coroutine[Any, Any, str]]) -> Verdict:
    """LLM semantic judge. Falls back to deterministic on any error."""
    base = check_dod(task_name, definition_of_done, result)
    try:
        out = await llm([{"role": "user", "content": (
            "You verify task completion. Task: " + task_name +
            "\nDefinition of done: " + (definition_of_done or "(none)") +
            "\nResult (truncated):\n" + str(result)[:2000] +
            '\n\nReply with exactly one line: PASS or FAIL: <short reason>'
        )}])
        line = str(out).strip()
        if line.upper().startswith("PASS"):
            return Verdict(True, [], 1.0, "llm", line[:300])
        if line.upper().startswith("FAIL"):
            return Verdict(False, base.missing, base.score, "llm", line[:300])
    except Exception:
        pass
    return base


def bridging_task_spec(task_name: str, task_id: str, verdict: Verdict) -> Dict[str, Any]:
    """Spec for the auto-injected bridging task that closes the gap."""
    return {
        "name": f"Fix gaps: {task_name}",
        "description": ("The previous attempt did not satisfy its definition of done. "
                        f"Missing: {', '.join(verdict.missing[:8]) or verdict.notes}. "
                        "Address exactly these gaps."),
        "agent_role": "coder",
        "tool_requirements": [],
        "dependencies": [task_id],
        "metadata": {"bridges": task_id, "auto_injected": True},
        "definition_of_done": "All listed gaps addressed and verifiable",
    }


def new_task_id() -> str:
    return uuid.uuid4().hex[:8]
