#!/usr/bin/env python3
"""Lint an OKF LLM Wiki bundle. Stdlib only."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from okf_common import EXTERNAL_RE, load_bundle, valid_iso8601

# Map common alternate field names to OKF reserved names.
# These are the mistakes humans and LLMs most often make when writing frontmatter.
MISUSE = {"name": "title", "url": "resource", "updated": "timestamp", "date": "timestamp", "modified": "timestamp", "label": "title"}
FACTUAL_TYPES = {"Source", "Note"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint OKF LLM Wiki bundle")
    ap.add_argument("bundle_dir")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stale-days", type=int, default=90)
    args = ap.parse_args()

    root = Path(args.bundle_dir).resolve()
    concepts = load_bundle(root)
    by_rel = {c.rel: c for c in concepts}

    errors: list[dict] = []
    warnings: list[dict] = []

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

    for c in concepts:
        fm = c.frontmatter
        if not c.is_reserved_file:
            if not str(fm.get("type", "")).strip():
                errors.append({"file": c.rel, "rule": "missing-type", "message": "no `type` field"})
            for bad, good in MISUSE.items():
                if bad in fm:
                    errors.append({"file": c.rel, "rule": "reserved-field-misuse", "message": f"uses `{bad}`; use `{good}`"})

        if "timestamp" in fm and not valid_iso8601(fm["timestamp"]):
            errors.append({"file": c.rel, "rule": "bad-timestamp", "message": f"not ISO 8601: {fm['timestamp']!r}"})

        if not c.is_reserved_file:
            for tgt in c.links:
                if tgt not in by_rel and not (root / tgt.lstrip("/")).exists():
                    errors.append({"file": c.rel, "rule": "broken-link", "message": f"missing {tgt}"})

        if not c.is_reserved_file and str(fm.get("type", "")) in FACTUAL_TYPES:
            src = fm.get("sources")
            if not src:
                warnings.append({"file": c.rel, "rule": "missing-sources", "message": "factual page has no `sources`"})
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
                        errors.append({"file": c.rel, "rule": "unresolvable-source", "message": f"sources target does not exist: {s}"})

        if str(fm.get("confidence", "")).lower() == "high" and valid_iso8601(fm.get("timestamp")):
            try:
                ts = datetime.fromisoformat(str(fm["timestamp"]).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if (now - ts).days > args.stale_days:
                    warnings.append({"file": c.rel, "rule": "stale-high-confidence", "message": f"high confidence but older than {args.stale_days}d"})
            except Exception:
                pass

    for c in concepts:
        if not c.is_reserved_file and c.rel != "/index.md" and incoming.get(c.rel, 0) == 0:
            warnings.append({"file": c.rel, "rule": "orphan", "message": "no incoming links"})

    ok = len(errors) == 0

    if args.json:
        print(json.dumps({"bundle": str(root), "pages": len([c for c in concepts if not c.is_reserved_file]), "errors": errors, "warnings": warnings, "ok": ok}, indent=2))
    else:
        print(f"OKF lint: {root}")
        print(f"  concept pages: {len([c for c in concepts if not c.is_reserved_file])}")
        print(f"  errors:   {len(errors)}")
        print(f"  warnings: {len(warnings)}")
        for item in errors + warnings:
            tag = "ERR" if item in errors else "WARN"
            print(f"  [{tag}] {item['file']}  {item['rule']}: {item['message']}")
        print("  RESULT:", "CONFORMANT" if ok else "NON-CONFORMANT")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
