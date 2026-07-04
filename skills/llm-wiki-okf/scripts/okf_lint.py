#!/usr/bin/env python3
"""Lint an OKF LLM Wiki bundle. Stdlib only."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from okf_common import (
    EXTERNAL_RE,
    FACTUAL_TYPES,
    load_bundle,
    resolve_bundles,
    resolve_single_bundle,
    valid_iso8601,
)

# Map common alternate field names to OKF reserved names.
# These are the mistakes humans and LLMs most often make when writing frontmatter.
MISUSE = {
    "name": "title",
    "url": "resource",
    "updated": "timestamp",
    "date": "timestamp",
    "modified": "timestamp",
    "label": "title",
}


def _lint_bundle(root: Path, args: argparse.Namespace) -> tuple[list[dict], list[dict], int]:
    """Run all lint checks on one bundle. Returns (errors, warnings, page_count)."""
    concepts = load_bundle(root)
    by_rel = {c.rel: c for c in concepts}

    errors: list[dict] = []
    warnings: list[dict] = []

    # ── Incoming link counts (for orphan detection) ────────────────────
    incoming: dict[str, int] = {c.rel: 0 for c in concepts}
    for c in concepts:
        if c.is_reserved_file:
            # Links from index.md / log.md / readme.md do not count toward "is this page
            # referenced by a real concept page" — otherwise every index rebuild would
            # trivially satisfy the orphan check for every page.
            continue
        for tgt in c.links:
            if tgt in incoming:
                incoming[tgt] += 1

    now = datetime.now(timezone.utc)

    # ── Per-page checks ───────────────────────────────────────────────
    for c in concepts:
        fm = c.frontmatter

        if not c.is_reserved_file:
            # Missing type
            if not str(fm.get("type", "")).strip():
                errors.append({
                    "file": c.rel,
                    "rule": "missing-type",
                    "message": "no `type` field",
                })

            # Reserved-field misuse
            for bad, good in MISUSE.items():
                if bad in fm:
                    errors.append({
                        "file": c.rel,
                        "rule": "reserved-field-misuse",
                        "message": f"uses `{bad}`; use `{good}`",
                    })

            # Strict-frontmatter: detect probable yamlish parser failures.
            # The yamlish parser supports flat key:value, inline lists, and
            # block lists, but silently drops nested maps, multiline scalars,
            # trailing comments, and tab-indented lists. These checks flag
            # keys whose values look like parse failures.
            if args.strict_frontmatter:
                # Check for empty-list keys that might indicate unparseable content
                for k, v in fm.items():
                    if isinstance(v, list) and len(v) == 0 and k not in ("tags", "sources"):
                        warnings.append({
                            "file": c.rel,
                            "rule": "suspicious-empty-list",
                            "message": (
                                f"field `{k}` is an empty list — may indicate "
                                f"yamlish parser couldn't parse the value. "
                                f"Use inline `[{k}: [a, b]]` or flat `{k}: value` syntax."
                            ),
                        })

        # Bad timestamps
        if "timestamp" in fm and not valid_iso8601(fm["timestamp"]):
            errors.append({
                "file": c.rel,
                "rule": "bad-timestamp",
                "message": f"not ISO 8601: {fm['timestamp']!r}",
            })

        # Broken cross-links
        if not c.is_reserved_file:
            for tgt in c.links:
                if tgt not in by_rel and not (root / tgt.lstrip("/")).exists():
                    errors.append({
                        "file": c.rel,
                        "rule": "broken-link",
                        "message": f"missing {tgt}",
                    })

        # Factual page missing sources
        if not c.is_reserved_file and str(fm.get("type", "")) in FACTUAL_TYPES:
            src = fm.get("sources")
            if not src:
                warnings.append({
                    "file": c.rel,
                    "rule": "missing-sources",
                    "message": "factual page has no `sources`",
                })
            else:
                src_list = src if isinstance(src, list) else [src]
                for s in src_list:
                    s = str(s).strip()
                    if not s:
                        continue
                    if EXTERNAL_RE.match(s):
                        continue
                    target = root / s.lstrip("/")
                    if not target.exists():
                        errors.append({
                            "file": c.rel,
                            "rule": "unresolvable-source",
                            "message": f"sources target does not exist: {s}",
                        })

        # Stale high-confidence pages
        if (
            str(fm.get("confidence", "")).lower() == "high"
            and valid_iso8601(fm.get("timestamp"))
        ):
            try:
                ts = datetime.fromisoformat(
                    str(fm["timestamp"]).replace("Z", "+00:00")
                )
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if (now - ts).days > args.stale_days:
                    warnings.append({
                        "file": c.rel,
                        "rule": "stale-high-confidence",
                        "message": (
                            f"high confidence but older than {args.stale_days}d"
                        ),
                    })
            except Exception:
                pass

    # ── Orphan detection ──────────────────────────────────────────────
    for c in concepts:
        if (
            not c.is_reserved_file
            and c.rel != "/index.md"
            and incoming.get(c.rel, 0) == 0
        ):
            warnings.append({
                "file": c.rel,
                "rule": "orphan",
                "message": "no incoming links",
            })

    # ── Contradiction detection ───────────────────────────────────────
    # Rule: duplicate-source-claim — two Source/Note pages citing the same
    # raw/<file> with different title values. Indicates two pages describe
    # the same source but disagree on what it's about.
    sources_map: dict[str, list[tuple[str, str]]] = {}  # raw_rel → [(page_rel, title)]
    for c in concepts:
        if c.is_reserved_file:
            continue
        if c.type_tag not in FACTUAL_TYPES:
            continue
        src = c.frontmatter.get("sources")
        if not src:
            continue
        src_list = src if isinstance(src, list) else [src]
        title = str(c.frontmatter.get("title", c.rel))
        for s in src_list:
            s = str(s).strip()
            if not s or EXTERNAL_RE.match(s):
                continue
            sources_map.setdefault(s, []).append((c.rel, title))

    for src_ref, claimants in sources_map.items():
        if len(claimants) <= 1:
            continue
        # Check if titles differ
        titles = {title for _, title in claimants}
        if len(titles) > 1:
            pages = ", ".join(rel for rel, _ in claimants)
            errors.append({
                "file": "N/A (multiple pages)",
                "rule": "duplicate-source-claim",
                "message": (
                    f"{len(claimants)} pages cite `{src_ref}` with "
                    f"different titles: {pages}"
                ),
            })

    # Rule: near-duplicate-title — two pages in the same subdirectory (e.g.
    # entities/ or concepts/) with the same or very similar title but
    # different sources, suggesting potential duplication.
    title_pages: dict[str, list[tuple[str, str]]] = {}  # dir/title_lower → [(rel, sources)]
    for c in concepts:
        if c.is_reserved_file:
            continue
        title = str(c.frontmatter.get("title", "")).strip().lower()
        if not title:
            continue
        key = f"{c.path.parent.name}/{title}"
        src = c.frontmatter.get("sources")
        src_str = ", ".join(str(s) for s in (src if isinstance(src, list) else [src or ""]))
        title_pages.setdefault(key, []).append((c.rel, src_str))

    for key, claimants in title_pages.items():
        if len(claimants) <= 1:
            continue
        pages = ", ".join(rel for rel, _ in claimants)
        warnings.append({
            "file": "N/A (multiple pages)",
            "rule": "near-duplicate-title",
            "message": (
                f"pages with similar title '{key}': {pages}"
            ),
        })

    page_count = len([c for c in concepts if not c.is_reserved_file])
    return errors, warnings, page_count


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint OKF LLM Wiki bundle")
    ap.add_argument("bundle_dir", nargs="?", default=None, help="Bundle path")
    ap.add_argument("--bundle", default=None, help="Explicit bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stale-days", type=int, default=90)
    ap.add_argument("--strict-frontmatter", action="store_true",
                    help="Warn on probable yamlish parser failures")
    args = ap.parse_args()

    # Resolve bundle(s)
    bundle_path = args.bundle or args.bundle_dir
    if bundle_path:
        resolved = resolve_single_bundle(bundle_path)
        if resolved is None:
            print(f"Bundle not found: {bundle_path}", file=sys.stderr)
            return 1
        bundles = [resolved]
    else:
        bundles = resolve_bundles(args.tier)
        if not bundles:
            print(f"No bundle found for tier '{args.tier}'", file=sys.stderr)
            return 1

    all_errors: list[dict] = []
    all_warnings: list[dict] = []
    total_pages = 0

    for tier_label, root in bundles:
        errors, warnings, page_count = _lint_bundle(root, args)
        if args.tier == "all":
            for e in errors:
                e["tier"] = tier_label
            for w in warnings:
                w["tier"] = tier_label
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        total_pages += page_count

    ok = len(all_errors) == 0

    if args.json:
        print(json.dumps({
            "bundle": [str(b[1]) for b in bundles],
            "pages": total_pages,
            "errors": all_errors,
            "warnings": all_warnings,
            "ok": ok,
        }, indent=2))
    else:
        tier_tag = f"  tier: {args.tier}" if args.tier != "local" else ""
        print(f"OKF lint: {', '.join(str(b[1]) for b in bundles)}{tier_tag}")
        print(f"  concept pages: {total_pages}")
        print(f"  errors:   {len(all_errors)}")
        print(f"  warnings: {len(all_warnings)}")
        for item in all_errors + all_warnings:
            tag = "ERR" if item in all_errors else "WARN"
            tier_str = f" [{item['tier']}]" if "tier" in item else ""
            print(
                f"  [{tag}]{tier_str} {item['file']}  "
                f"{item['rule']}: {item['message']}"
            )
        print("  RESULT:", "CONFORMANT" if ok else "NON-CONFORMANT")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
