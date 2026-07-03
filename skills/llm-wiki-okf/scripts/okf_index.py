#!/usr/bin/env python3
"""Rebuild directory index.md files in an OKF bundle. Stdlib only."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from okf_common import MARKER, MARKER_CLOSE, load_bundle, now_iso


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild OKF directory indexes")
    ap.add_argument("bundle_dir")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    root = Path(args.bundle_dir).resolve()
    concepts = load_bundle(root)

    by_dir: dict[Path, list] = defaultdict(list)
    for c in concepts:
        if not c.is_reserved_file:
            by_dir[c.path.parent].append(c)

    changed = 0
    for directory, pages in sorted(by_dir.items()):
        pages.sort(key=lambda c: str(c.frontmatter.get("title") or c.path.stem).lower())
        lines = [MARKER, ""]
        for c in pages:
            title = c.frontmatter.get("title") or c.path.stem
            rel = "/" + str(c.path.relative_to(root)).replace("\\", "/")
            desc = c.frontmatter.get("description")
            entry = f"- [{title}]({rel})"
            if desc:
                entry += f" — {desc}"
            lines.append(entry)
        lines.append("")
        lines.append(MARKER_CLOSE)
        lines.append("")
        auto_block = "\n".join(lines)

        idx_path = directory / "index.md"
        if idx_path.exists():
            existing = idx_path.read_text(encoding="utf-8", errors="replace")
            if MARKER in existing and MARKER_CLOSE in existing:
                # Replace everything between (and including) the marker pair.
                before, _, rest = existing.partition(MARKER)
                _, _, after = rest.partition(MARKER_CLOSE)
                head = before.rstrip() + "\n\n"
                tail = after.lstrip("\n")
            elif MARKER in existing:
                # Legacy single-marker file: migrate to the pair form; drop old auto content.
                head = existing.split(MARKER, 1)[0].rstrip() + "\n\n"
                tail = ""
            else:
                head = existing.rstrip() + "\n\n"
                tail = ""
        else:
            dir_title = directory.name.replace("-", " ").title() if directory != root else root.name.replace("-", " ").title()
            head = f"---\ntype: Index\ntitle: {dir_title}\ntimestamp: {now_iso()}\n---\n\n# {dir_title}\n\n"
            tail = ""

        new_content = head + auto_block + ("\n" + tail if tail else "")
        if args.dry_run:
            print(f"[dry-run] {idx_path} ({len(pages)} pages)")
        elif not idx_path.exists() or idx_path.read_text(encoding="utf-8", errors="replace") != new_content:
            idx_path.write_text(new_content, encoding="utf-8")
            changed += 1
            print(f"updated {idx_path} ({len(pages)} pages)")

    if not args.dry_run:
        print(f"Rebuilt indexes. Changed: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
