#!/usr/bin/env python3
"""Print resolved bundle directories. Stdlib only."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from okf_common import load_bundle, resolve_bundles, resolve_single_bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="Show wiki bundle directory info")
    ap.add_argument("--bundle", default=None, help="Explicit bundle path")
    ap.add_argument("--tier", default="all", choices=["local", "global", "all"],
                    help="Tier selector (default: all)")
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
            print("No bundles found.", file=sys.stderr)
            return 1
    if not bundles:
        print("No bundles found.", file=sys.stderr)
        return 1

    output = []
    for tier_label, root in bundles:
        concepts = load_bundle(root)
        pages = [c for c in concepts if not c.is_reserved_file]
        raw_count = 0
        raw_dir = root / "raw"
        if raw_dir.is_dir():
            raw_count = len([
                f for f in raw_dir.iterdir()
                if f.is_file() and not f.name.startswith(".")
            ])
        output.append({
            "tier": tier_label,
            "path": str(root.resolve()),
            "exists": root.is_dir(),
            "populated": len(pages) > 0 or raw_count > 0,
            "pages": len(pages),
            "raw_files": raw_count,
        })

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for entry in output:
            tier_tag = f"[{entry['tier']}] " if entry['tier'] else ""
            print(f"{tier_tag}{entry['path']}")
            print(f"  exists:    {entry['exists']}")
            print(f"  populated: {entry['populated']}")
            print(f"  pages:     {entry['pages']}")
            print(f"  raw files: {entry['raw_files']}")
            print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
