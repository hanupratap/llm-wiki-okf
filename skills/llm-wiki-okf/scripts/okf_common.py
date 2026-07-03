"""Shared helpers for OKF bundle scripts. Stdlib only."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESERVED_FIELDS = ("type", "title", "description", "resource", "tags", "timestamp")
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+?\.md)(?:#[^)]*)?\)")
MARKER = "<!-- okf:auto-index -->"
MARKER_CLOSE = "<!-- /okf:auto-index -->"
# Targets starting with a scheme (http://, https://, file://, ...) are external and must
# not be normalized as bundle-relative paths.
EXTERNAL_RE = re.compile(r"^[a-z][a-z0-9+.-]*://", re.IGNORECASE)


def now_iso() -> str:
    """Current UTC time as ISO 8601, e.g. 2026-07-03T14:30:00Z."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_frontmatter(md_text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Empty dict if no frontmatter block."""
    m = FRONTMATTER_RE.match(md_text)
    if not m:
        return {}, md_text
    return _parse_yamlish(m.group(1)), md_text[m.end():]


def _parse_yamlish(text: str) -> dict[str, Any]:
    """Tiny parser for flat frontmatter.

    Supports:
      - key: value
      - key: [a, b, c]        (inline list)
      - key:                  (block list, one `- item` per following indented line)
    """
    out: dict[str, Any] = {}
    current_key: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            current_key = None
            continue
        # Indented `- item` continues a block list for the most recent key.
        if stripped.startswith("- ") and current_key is not None:
            item = stripped[2:].strip().strip("'\"")
            if item:
                out.setdefault(current_key, []).append(item)
            continue
        if ":" not in line:
            current_key = None
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            items = [x.strip().strip("'\"") for x in inner.split(",")] if inner else []
            out[key] = [x for x in items if x]
            current_key = None
        elif val == "":
            # Empty value: start a block list that following `- ` lines will populate.
            out[key] = []
            current_key = key
        else:
            out[key] = val.strip("'\"")
            current_key = None
    return out


@dataclass
class Concept:
    path: Path
    rel: str
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    links: list[str] = field(default_factory=list)

    @property
    def is_reserved_file(self) -> bool:
        # Reserved filenames are not concept pages and are exempt from concept-level checks.
        # Keep this list format-agnostic; add agent-specific names only via local config.
        return self.path.name.lower() in {
            "index.md", "log.md", "readme.md"
        }


def _rel_target(link: str, from_rel: str) -> str:
    """Normalize a markdown link target to a bundle-root-relative path.

    External URLs (http(s)://, etc.) are returned unchanged so callers can skip them.
    """
    if EXTERNAL_RE.match(link):
        return link
    if link.startswith("/"):
        return link
    from_dir = "/".join(from_rel.split("/")[:-1])
    combined = (from_dir + "/" + link).lstrip("/")
    parts: list[str] = []
    for seg in combined.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/" + "/".join(parts)


def load_bundle(root: str | Path) -> list[Concept]:
    """Load all markdown files under root as Concept objects. Skip raw/ and hidden dirs."""
    root = Path(root).resolve()
    concepts: list[Concept] = []
    for path in sorted(root.rglob("*.md")):
        rel_parts = path.relative_to(root).parts
        if rel_parts and rel_parts[0] == "raw":
            continue
        if any(p.startswith(".") for p in rel_parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm, body = parse_frontmatter(text)
        rel = "/" + str(path.relative_to(root)).replace("\\", "/")
        links = [_rel_target(t, rel) for t in MD_LINK_RE.findall(body)]
        links = [t for t in links if not EXTERNAL_RE.match(t)]
        concepts.append(Concept(path=path, rel=rel, frontmatter=fm, body=body, links=links))
    return concepts


def valid_iso8601(value: Any) -> bool:
    if not isinstance(value, str):
        return isinstance(value, datetime)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except Exception:
        return False
