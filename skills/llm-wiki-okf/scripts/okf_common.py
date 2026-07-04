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

# Page types that are considered factual — they must have a `sources` field.
FACTUAL_TYPES = {"Source", "Note"}

# ── Tier resolution ────────────────────────────────────────

BUNDLE_GLOBAL = Path.home() / ".llm-wiki"
BUNDLE_LOCAL = Path(".llm-wiki").resolve()


def resolve_bundles(tier: str = "local") -> list[tuple[str, Path]]:
    """Resolve wiki bundle paths for a tier selector.

    Returns list of (label, path) tuples — global first when tiers are merged,
    so per-tier output is naturally ordered.
    """
    bundles: list[tuple[str, Path]] = []
    if tier in ("global", "all"):
        if BUNDLE_GLOBAL.is_dir():
            bundles.append(("global", BUNDLE_GLOBAL))
    if tier in ("local", "all"):
        if BUNDLE_LOCAL.is_dir():
            bundles.append(("local", BUNDLE_LOCAL))
    return bundles


def resolve_single_bundle(path: str | Path | None, tier: str = "local") -> tuple[str, Path] | None:
    """Resolve a single bundle from an explicit path or tier selector.

    If *path* is given, return it (no tier label).
    Otherwise resolve via *tier*; return the first match, or None.
    """
    if path is not None:
        p = Path(path).resolve()
        return ("", p) if p.is_dir() else None
    bundles = resolve_bundles(tier)
    if bundles:
        return bundles[0]
    return None


# ── Tokens & search ────────────────────────────────────────

# Stopwords: very common English terms that add noise to search ranking.
_STOPWORDS: set[str] = {
    "and", "the", "this", "that", "with", "from", "have", "been", "were", 
    "they", "their", "them", "will", "would", "could", "should",
    "about", "there", "which", "what", "when", "where", "than",
    "then", "also", "just", "more", "some", "such", "only", "other",
    "into", "over", "very", "after", "before", "because", "between",
    "through", "during", "without", "within", "along", "these", "those",
    "does", "being", "its", "been",
}


def tokenize_query(query: str) -> list[str]:
    """Tokenize a search query for bundle search.

    Lowercases, strips punctuation, splits on whitespace, removes
    stopwords and very short tokens. Returns unique tokens in order.
    """
    normalized = query.lower()
    normalized = re.sub(r"[\-_./\\]+", " ", normalized)
    normalized = re.sub(r"[\W_]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    seen: set[str] = set()
    tokens: list[str] = []
    for token in normalized.split():
        token = token.strip()
        if len(token) < 2:
            continue
        if token in _STOPWORDS:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _term_hits(text: str, terms: list[str]) -> int:
    """Count how many *terms* appear in *text* (case-insensitive)."""
    if not text:
        return 0
    lowered = text.lower()
    return sum(1 for t in terms if t in lowered)


def search_bundle(root: Path, query: str, max_results: int = 10) -> list[dict]:
    """Search a bundle for pages matching *query*.

    Scoring: frontmatter fields (title, aliases, tags, description) get
    higher weights; body content gets a baseline weight. Results are
    ranked by total score descending.
    """
    concepts = load_bundle(root)
    terms = tokenize_query(query)
    if not terms:
        return []

    scored: list[dict] = []
    for c in concepts:
        if c.is_reserved_file:
            continue

        fm = c.frontmatter
        score = 0

        # Identity fields — highest weight
        score += _term_hits(str(fm.get("title", "")), terms) * 6
        score += _term_hits(c.rel, terms) * 4

        # Metadata fields
        for field, weight in [
            ("aliases", 5),
            ("description", 4),
            ("tags", 3),
            ("type", 2),
            ("category", 2),
            ("domain", 2),
        ]:
            val = fm.get(field)
            if isinstance(val, list):
                score += _term_hits(" ".join(str(v) for v in val), terms) * weight
            else:
                score += _term_hits(str(val), terms) * weight

        # Body — baseline
        score += _term_hits(c.body, terms) * 1

        if score > 0:
            title = str(fm.get("title") or c.rel.split("/")[-1].replace(".md", ""))
            page_type = str(fm.get("type", "page"))
            desc = str(fm.get("description", ""))
            # Preview: first ~200 chars of body
            preview = c.body.strip()[:200].replace("\n", " ")
            if len(c.body.strip()) > 200:
                preview += "…"

            scored.append({
                "rel": c.rel,
                "title": title,
                "type": page_type,
                "description": desc,
                "preview": preview,
                "score": score,
                "path": str(c.path),
            })

    scored.sort(key=lambda r: (-r["score"], r["rel"]))
    return scored[:max_results]


# ── Frontmatter & file helpers ─────────────────────────────

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
      - key: value           (plain scalar, quotes stripped)
      - key: [a, b, c]       (inline list)
      - key:                 (block list, one `- item` per following indented line)

    NOT supported (the yamlish subset is deliberate — keep frontmatter
    flat and predictable):
      - nested mappings (e.g. ``key: { sub: val }``)
      - multiline string values (``>`` / ``|``)
      - inline comments after a value on the same line
      - tabs as indentation
      - quoted keys containing ``:``
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


def bump_timestamp(path: Path) -> None:
    """Bump the `timestamp` field in a markdown file's frontmatter."""
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(text)
    new_ts = now_iso()
    fm["timestamp"] = new_ts

    # Rebuild frontmatter block
    lines: list[str] = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    new_text = "\n".join(lines) + "\n\n" + body.lstrip()

    if new_text != text:
        path.write_text(new_text, encoding="utf-8")


def slugify(s: str) -> str:
    """Derive a safe slug from a string."""
    slug = re.sub(r"[^\w\s-]", "", s.lower())
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug.strip("-")[:80] or "untitled"


# ── Concept dataclass ─────────────────────────────────────

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

    @property
    def type_tag(self) -> str:
        return str(self.frontmatter.get("type", "page"))


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
