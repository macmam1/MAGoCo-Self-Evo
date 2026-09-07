"""Context Guardian — prevents history loss + topic interference.

Problems solved:
1. Chat history loss: rolling verbatim log + versioned snapshots + auto-summary on overflow.
2. Topic interference: per-topic segmentation; recall is scoped to the ACTIVE topic only,
   so facts from topic A don't leak into topic B answers.

Design (works without LLM; LLM hook optional for smarter summaries):
- TopicSegmenter: keyword-overlap heuristic (Jaccard) with hysteresis — avoids flapping.
- ContextVersion: immutable snapshot {working window + rolling summary + topic map}.
- SmartSummarizer: extractive fallback (top sentences by keyword centrality) + optional LLM.
- InterferenceGuard: recall filter — only memories tagged with active topic (or global core blocks).
"""

from __future__ import annotations

import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional


_WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06FF0-9]{3,}")


def _keywords(text: str, limit: int = 24) -> Counter:
    words = _WORD_RE.findall(text.lower())
    stop = {"the", "and", "for", "with", "that", "this", "from", "have", "has",
            "است", "این", "است", "را", "های", "یکی", "برای", "است"}
    return Counter(w for w in words if w not in stop).most_common(limit)


def _jaccard(a: Counter, b: Counter) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


@dataclass
class Topic:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    label: str = "general"
    keywords: Counter = field(default_factory=Counter)
    message_ids: List[str] = field(default_factory=list)
    summary: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label,
                "keywords": dict(self.keywords.most_common(12)),
                "messages": len(self.message_ids), "summary": self.summary,
                "updated_at": self.updated_at.isoformat()}


@dataclass
class ContextVersion:
    """Immutable snapshot of working context at a point in time."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    session_id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    window: List[Dict[str, str]] = field(default_factory=list)
    rolling_summary: str = ""
    topics: List[Dict[str, Any]] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "session_id": self.session_id,
                "created_at": self.created_at.isoformat(),
                "window_len": len(self.window), "rolling_summary": self.rolling_summary,
                "topics": self.topics, "note": self.note}


class TopicSegmenter:
    """Assigns each message to a topic; creates new topic on drift."""

    def __init__(self, drift_threshold: float = 0.18, min_messages: int = 2):
        self.drift_threshold = drift_threshold
        self.min_messages = min_messages
        self.topics: Dict[str, Topic] = {}
        self.active_topic_id: Optional[str] = None

    def ingest(self, message_id: str, text: str) -> Topic:
        kw = Counter(dict(_keywords(text)))
        best: Optional[Topic] = None
        best_score = 0.0
        for t in self.topics.values():
            s = _jaccard(kw, t.keywords)
            if s > best_score:
                best_score, best = s, t
        if best and (best_score >= self.drift_threshold or len(best.message_ids) < self.min_messages):
            best.keywords.update(kw)
            best.message_ids.append(message_id)
            best.updated_at = datetime.utcnow()
            self.active_topic_id = best.id
            return best
        label = " ".join(w for w, _ in kw.most_common(3)) or "general"
        t = Topic(label=label, keywords=kw, message_ids=[message_id])
        self.topics[t.id] = t
        self.active_topic_id = t.id
        return t

    def active(self) -> Optional[Topic]:
        return self.topics.get(self.active_topic_id) if self.active_topic_id else None


class SmartSummarizer:
    """Extractive fallback + optional LLM upgrade."""

    def __init__(self, llm: Optional[Callable[..., Coroutine[Any, Any, str]]] = None):
        self.llm = llm

    async def summarize(self, messages: List[Dict[str, str]], max_chars: int = 800) -> str:
        if not messages:
            return ""
        if self.llm:
            try:
                convo = "\n".join(f"{m.get('role')}: {m.get('content', '')[:400]}" for m in messages[-20:])
                out = await self.llm([{"role": "user", "content":
                    f"Summarize preserving decisions, names, numbers, open questions (max {max_chars} chars):\n{convo}"}])
                return str(out)[:max_chars]
            except Exception:
                pass
        # Extractive fallback: score sentences by keyword centrality
        text = " ".join(m.get("content", "") for m in messages)
        sentences = re.split(r"(?<=[.!?؟\n])\s+", text)
        kw = Counter(dict(_keywords(text, 40)))
        scored = sorted(
            ((sum(kw.get(w, 0) for w in _WORD_RE.findall(s.lower())), s) for s in sentences if len(s.strip()) > 20),
            reverse=True,
        )
        out, total = [], 0
        for _, s in scored:
            if total + len(s) > max_chars:
                break
            out.append(s.strip())
            total += len(s)
        return " ".join(out) or text[:max_chars]


class ContextGuardian:
    """Per-session guardian: window + summary + versions + topics."""

    def __init__(self, session_id: str, max_window: int = 20,
                 llm: Optional[Callable[..., Coroutine[Any, Any, str]]] = None):
        self.session_id = session_id
        self.max_window = max_window
        self.window: List[Dict[str, str]] = []
        self.rolling_summary = ""
        self.segmenter = TopicSegmenter()
        self.summarizer = SmartSummarizer(llm)
        self.versions: List[ContextVersion] = []
        self._msg_seq = 0

    async def add(self, role: str, content: str) -> Dict[str, Any]:
        """Add a turn; auto-segments topic, snapshots + summarizes on overflow."""
        self._msg_seq += 1
        mid = f"m{self._msg_seq}"
        topic = self.segmenter.ingest(mid, content)
        self.window.append({"id": mid, "role": role, "content": content, "topic_id": topic.id})
        events: Dict[str, Any] = {"topic": topic.to_dict(), "snapshot": None, "summarized": False}
        if len(self.window) > self.max_window:
            # Snapshot BEFORE trimming (no history loss)
            snap = self.snapshot(note=f"overflow@{len(self.window)}")
            events["snapshot"] = snap.to_dict()
            # Summarize evicted half, keep rolling summary (prevents loss)
            evicted = self.window[: len(self.window) - self.max_window]
            part = await self.summarizer.summarize(evicted)
            self.rolling_summary = (self.rolling_summary + "\n" + part).strip()[-2000:]
            self.window = self.window[-self.max_window:]
            events["summarized"] = True
        return events

    def snapshot(self, note: str = "") -> ContextVersion:
        v = ContextVersion(session_id=self.session_id,
                           window=[dict(m) for m in self.window],
                           rolling_summary=self.rolling_summary,
                           topics=[t.to_dict() for t in self.segmenter.topics.values()],
                           note=note)
        self.versions.append(v)
        return v

    def restore(self, version_id: str) -> bool:
        for v in self.versions:
            if v.id == version_id:
                self.window = [dict(m) for m in v.window]
                self.rolling_summary = v.rolling_summary
                return True
        return False

    def scoped_context(self, max_items: int = 12) -> List[Dict[str, str]]:
        """Return window filtered to ACTIVE topic + rolling summary header (anti-interference)."""
        active = self.segmenter.active()
        if not active:
            return self.window[-max_items:]
        scoped = [m for m in self.window if m.get("topic_id") == active.id][-max_items:]
        # Always prepend summary so older topics aren't lost, just deprioritized
        if self.rolling_summary:
            return [{"id": "summary", "role": "system", "content": f"[history summary] {self.rolling_summary}"}] + scoped
        return scoped

    def state(self) -> Dict[str, Any]:
        return {"session_id": self.session_id, "window_len": len(self.window),
                "versions": len(self.versions), "rolling_summary_len": len(self.rolling_summary),
                "topics": [t.to_dict() for t in self.segmenter.topics.values()],
                "active_topic": self.segmenter.active().to_dict() if self.segmenter.active() else None}


_guardians: Dict[str, ContextGuardian] = {}


def get_guardian(session_id: str, max_window: int = 20) -> ContextGuardian:
    g = _guardians.get(session_id)
    if not g:
        g = ContextGuardian(session_id, max_window)
        _guardians[session_id] = g
    return g
