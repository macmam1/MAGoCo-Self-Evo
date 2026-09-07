"""Skill importer — fetch any SKILL.md by URL, validate, register natively.

Supports the open Agent Skills layout (SKILL.md with YAML frontmatter):
  ---
  name: my-skill
  description: What it does
  ---
  <markdown instructions...>

Also accepts raw GitHub blob URLs (auto-converted to raw.githubusercontent).
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

import httpx

from magoco_core.skills.models import (
    SkillCategory, SkillType, SkillStatus, SkillManifest,
    SecurityLevel, ExecutionMode,
)


def github_blob_to_raw(url: str) -> str:
    """Convert github.com/<owner>/<repo>/blob/<ref>/<path> to raw URL."""
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/(.+)", url)
    if m:
        owner, repo, ref, path = m.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
    return url


def parse_skill_md(text: str, fallback_id: str = "imported-skill") -> Dict[str, Any]:
    """Parse SKILL.md frontmatter + body. Never throws on malformed input."""
    front: Dict[str, str] = {}
    body = text
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                front[k.strip().lower()] = v.strip().strip("\"'")
        body = m.group(2)
    name = front.get("name", fallback_id)
    return {
        "id": re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or fallback_id,
        "display_name": front.get("name", fallback_id),
        "description": front.get("description", body[:300].strip()),
        "body": body[:8000],
        "metadata": {"imported_frontmatter": front},
    }


async def fetch_skill_md(url: str, timeout: float = 20.0) -> str:
    """Download SKILL.md text from a URL (follows github blob -> raw)."""
    raw = github_blob_to_raw(url.rstrip("/"))
    if raw.endswith("/"):
        raw = raw + "SKILL.md"
    elif not raw.endswith(".md"):
        raw = raw.rstrip("/") + "/SKILL.md"
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(raw, headers={"User-Agent": "MAGoCo-Self-Evo/1.0"})
        r.raise_for_status()
        return r.text


def manifest_from_parsed(parsed: Dict[str, Any], category: str = "custom",
                         author: str = "imported",
                         source_url: str = "") -> SkillManifest:
    """Build a safe DRAFT manifest from parsed SKILL.md (prompt-type, no code exec)."""
    try:
        cat = SkillCategory(category)
    except ValueError:
        cat = SkillCategory.CUSTOM
    return SkillManifest(
        id=parsed["id"], name=parsed["id"],
        display_name=parsed.get("display_name", parsed["id"]),
        description=(parsed.get("description", "")[:500] +
                     (f"\n\nPrompt:\n{parsed.get('body', '')[:2000]}" if parsed.get("body") else "")),
        version="0.1.0",
        category=cat, type=SkillType.PROMPT,
        tags={"imported", "skill-md"},
        author=author,
        homepage=source_url, repository=source_url,
        entry_point="prompt", code_path="",
        execution_mode=ExecutionMode.SYNC,
        security_level=SecurityLevel.SAFE,
        status=SkillStatus.DRAFT,
    )


async def import_from_url(url: str, category: str = "custom",
                          author: str = "imported") -> SkillManifest:
    """Fetch + parse + build manifest (caller persists via registry)."""
    text = await fetch_skill_md(url)
    fallback = url.rstrip("/").split("/")[-2] if "/" in url else "imported-skill"
    parsed = parse_skill_md(text, fallback_id=fallback)
    return manifest_from_parsed(parsed, category=category, author=author, source_url=url)


def manifest_from_catalog(entry: Dict[str, Any]) -> SkillManifest:
    """Build a DRAFT marketplace entry from the curated seed catalog."""
    try:
        cat = SkillCategory(entry.get("category", "custom"))
    except ValueError:
        cat = SkillCategory.CUSTOM
    eid = entry["id"]
    return SkillManifest(
        id=eid, name=eid,
        display_name=entry.get("display_name", eid),
        description=entry.get("description", "")[:500],
        version="0.1.0",
        category=cat, type=SkillType.WORKFLOW,
        tags=set(entry.get("tags", [])) | {"curated", "marketplace"},
        author=entry.get("author", "curated"),
        homepage=entry.get("source_url", ""), repository=entry.get("source_url", ""),
        entry_point="prompt", code_path="",
        execution_mode=ExecutionMode.SYNC,
        security_level=SecurityLevel.SAFE,
        status=SkillStatus.PUBLISHED,
    )
