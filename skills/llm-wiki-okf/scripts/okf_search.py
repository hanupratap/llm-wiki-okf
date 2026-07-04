#!/usr/bin/env python3
"""Search an OKF bundle for pages matching a query. Stdlib only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from okf_common import (
    resolve_bundles,
    resolve_single_bundle,
    search_bundle,
    search_bundle as _search,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Search OKF LLM Wiki bundle")
    ap.add_argument("query", nargs="*", help="Search terms (omit for --tier status)")
    ap.add_argument("--bundle", default=None, help="Explicit bundle path")
    ap.add_argument("--tier", default="local",
                    choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--max-results", type=int, default=10,
                    help="Max results (default: 10)")
    ap.add_argument("--json", action="store_true",
                    help="JSON output")
    ap.add_argument("--toc", action="store_true",
                    help="Print a table-of-contents overview instead of ranked search")
    ap.add_argument("--include-archived", action="store_true",
                    help="Include archived pages in results (excluded by default)")
    args = ap.parse_args()

    query = " ".join(args.query).strip()

    if not query and not args.toc:
        ap.error("query required (or use --toc)")

    if args.bundle:
        resolved = resolve_single_bundle(args.bundle)
        if resolved is None or not resolved[1].is_dir():
            print(f"Bundle not found: {args.bundle}", file=sys.stderr)
            return 1
        bundles = [resolved]
    else:
        bundles = resolve_bundles(args.tier)
        if not bundles:
            print(f"No bundle found for tier '{args.tier}'", file=sys.stderr)
            return 1

    all_results: list[dict] = []
    for tier_label, root in bundles:
        if args.toc:
            # TOC mode: list pages grouped by type
            concepts = _search.__wrapped__ if hasattr(_search, "__wrapped__") else None
            from okf_common import load_bundle as _lb
            cs = _lb(root)
            by_type: dict[str, list] = {}
            for c in cs:
                if c.is_reserved_file:
                    continue
                if not args.include_archived and str(c.frontmatter.get("status", "")).strip() == "archived":
                    continue
                t = c.type_tag
                by_type.setdefault(t, []).append({
                    "rel": c.rel,
                    "title": c.frontmatter.get("title") or c.rel.split("/")[-1].replace(".md", ""),
                    "path": str(c.path),
                })
            for t, pages in sorted(by_type.items()):
                pages.sort(key=lambda p: p["title"].lower())
                for p in pages:
                    prefix = f"[{tier_label}] " if args.tier == "all" else ""
                    print(f"{prefix}[{t}] {p['title']}  ({p['rel']})")
        else:
            results = search_bundle(root, query, args.max_results, include_archived=args.include_archived)
            for r in results:
                if args.tier == "all":
                    r["tier"] = tier_label
            all_results.extend(results)

    if not args.toc:
        # Merge & re-rank when multi-tier
        if args.tier == "all":
            all_results.sort(key=lambda r: (-r["score"], r["rel"]))
            all_results = all_results[: args.max_results]

        if args.json:
            print(json.dumps({
                "query": query,
                "tier": args.tier,
                "results": all_results,
                "count": len(all_results),
            }, indent=2))
        else:
            print(f"Search: {query!r}")
            print(f"  tier: {args.tier}  results: {len(all_results)}\n")
            for i, r in enumerate(all_results, 1):
                tier_tag = f" [{r['tier']}]" if "tier" in r else ""
                print(
                    f"{i}. {r['title']}{tier_tag}  "
                    f"({r['type']})  score={r['score']}"
                )
                print(f"   {r['rel']}")
                if r.get("description"):
                    print(f"   {r['description']}")
                if r.get("preview"):
                    print(f"   {r['preview'][:120]}")
                print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
