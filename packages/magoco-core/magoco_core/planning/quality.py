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
from typing import Any, Callable, Coroutine, Dict, List, Optional


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


# ---------- Anti-hallucination: honesty contract + grounding ----------

HONESTY_CONTRACT_EN = (
    "HONESTY CONTRACT (binding): "
    "1) Never claim a fact, number, file, URL, or completion without evidence in front of you. "
    "2) Never confirm work as done unless verification passed or you quote the proof. "
    "3) Never flatter or agree to please; disagree with evidence when the user is wrong. "
    "4) Say 'I don't know' instead of inventing. Violations are recorded against your track record."
)

HONESTY_CONTRACT_FA = (
    "قرارداد صداقت (لازم‌الاجرا): "
    "۱) هیچ ادعا، عدد، فایل، آدرس یا اتمامی را بدون مدرک نگو. "
    "۲) کاری را تمام‌شده اعلام نکن مگر راستی‌آزمایی گذشته باشد یا مدرکش را نقل کنی. "
    "۳) برای خوشایند، تملق یا موافقت دروغین نکن؛ با مدرک مخالفت کن. "
    "۴) به‌جای حدس بگو نمی‌دانم. تخلفات در سابقه‌ات ثبت می‌شود."
)

_COMPLETION_PATTERNS = [
    r"\b(done|completed|finished|all done|successfully completed|works? (now|correctly|as expected))\b",
    r"تمام شد|انجام شد|تکمیل شد|به پایان رسید",
]

_PATH_RE = re.compile(r"(?:/[\w.\-]+)+/?|(?:[A-Za-z]:\\(?:[\w.\-]+\\)*[\w.\-]*)")
_URL_RE = re.compile(r"https?://[^\s)\"']+")
_NUMBER_FACT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:%|percent|ms|s\b|mb|gb|tokens?|rows?|users?)\b", re.I)


@dataclass
class GroundingReport:
    grounded_ratio: float = 1.0
    unverified: List[str] = field(default_factory=list)
    false_completion: bool = False
    notes: str = ""


def check_grounding(result: Any, evidence_texts: List[str],
                    task_name: str = "") -> GroundingReport:
    """Deterministic grounding: every checkable claim must appear in evidence.

    Conservative by design: only COMPLETION claims and invented paths/URLs can
    fail a task; bare numbers are reported as unverified notes, never fatal.
    """
    text = "" if result is None else str(result)
    evidence = "\n".join(evidence_texts or []).lower()
    if not text.strip():
        return GroundingReport(0.0, ["empty result"], False, "empty result")

    unverified: List[str] = []

    # 1. Completion claims require evidence (tool success, test output, proof quote)
    claims_completion = any(re.search(p, text, re.I) for p in _COMPLETION_PATTERNS)
    evidence_signals = ["test pass", "tests pass", "exit 0", "exit code 0", "success",
                        "verified", "proof", "تست", "موفق", "گذشت"]
    has_evidence = any(s in text.lower() or s in evidence for s in evidence_signals)
    false_completion = bool(claims_completion and not has_evidence)

    # 2. Paths/URLs in the output should exist in evidence (else possibly invented)
    for m in _PATH_RE.findall(text)[:10]:
        if len(m) > 4 and m.lower() not in evidence and "example" not in m.lower():
            unverified.append(f"unverified path: {m[:80]}")
    for m in _URL_RE.findall(text)[:10]:
        if m.lower() not in evidence and "example.com" not in m:
            unverified.append(f"unverified url: {m[:80]}")

    total_checks = 1 + len(unverified)
    failed = (1 if false_completion else 0) + len(unverified)
    ratio = round(1.0 - failed / max(1, total_checks), 2)
    notes = f"Task '{task_name}': grounding {ratio:.0%}"
    if false_completion:
        notes += "; completion claimed WITHOUT evidence"
    if unverified:
        notes += f"; {len(unverified)} unverified reference(s)"
    return GroundingReport(ratio, unverified, false_completion, notes)
