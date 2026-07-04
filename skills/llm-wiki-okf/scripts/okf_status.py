#!/usr/bin/env python3
"""Print OKF bundle health overview. Stdlib only."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from okf_common import load_bundle, resolve_bundles, resolve_single_bundle


def _bundle_status(root: Path) -> dict:
    """Return a status dict for one bundle."""
    concepts = load_bundle(root)
    pages = [c for c in concepts if not c.is_reserved_file]

    # Count by type
    type_counts: dict[str, int] = dict(Counter(c.type_tag for c in pages))

    # Last log entry
    log_path = root / "log.md"
    last_log = ""
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").strip().split("\n")
        for line in lines:
            if line.strip().startswith("- "):
                last_log = line.strip()[2:]
                break

    # Count source files in raw/
    raw_dir = root / "raw"
    raw_count = 0
    if raw_dir.is_dir():
        raw_count = len([
            f for f in raw_dir.iterdir()
            if f.is_file() and not f.name.startswith(".")
        ])

    return {
        "root": str(root),
        "page_count": len(pages),
        "types": type_counts,
        "raw_files": raw_count,
        "last_log": last_log,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="OKF bundle status")
    ap.add_argument("--bundle", default=None, help="Bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

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

    all_status = {}
    for tier_label, root in bundles:
        status = _bundle_status(root)
        label = tier_label or str(root)
        all_status[label] = status

    if args.json:
        print(json.dumps(all_status, indent=2))
    else:
        for label, s in all_status.items():
            prefix = f"[{label}] " if args.tier == "all" else ""
            print(f"OKF status: {prefix}{s['root']}")
            print(f"  pages:       {s['page_count']}")
            print(f"  by type:     {', '.join(f'{t}={n}' for t, n in sorted(s['types'].items()))}")
            print(f"  raw files:   {s['raw_files']}")
            if s["last_log"]:
                print(f"  last change: {s['last_log'][:80]}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
