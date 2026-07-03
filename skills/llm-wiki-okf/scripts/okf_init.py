#!/usr/bin/env python3
"""Scaffold a new OKF LLM Wiki bundle. Stdlib only."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from okf_common import MARKER, MARKER_CLOSE, now_iso


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold an OKF LLM Wiki bundle")
    ap.add_argument("bundle_dir")
    ap.add_argument("--title", default="Wiki")
    ap.add_argument("--no-git", action="store_true")
    args = ap.parse_args()

    root = Path(args.bundle_dir).resolve()
    ts = now_iso()

    for sub in ("raw", "sources", "entities", "concepts", "notes"):
        (root / sub).mkdir(parents=True, exist_ok=True)

    for sub in ("sources", "entities", "concepts", "notes"):
        idx = root / sub / "index.md"
        if not idx.exists():
            title = sub.replace("-", " ").title()
            idx.write_text(
                f"---\ntype: Index\ntitle: {title}\ntimestamp: {ts}\n---\n\n# {title}\n\n{MARKER}\n{MARKER_CLOSE}\n",
                encoding="utf-8",
            )

    root_index = root / "index.md"
    if not root_index.exists():
        section_links = (
            f"# {args.title}\n\n"
            "Sections:\n\n"
            f"- [Notes](/notes/index.md)\n"
            f"- [Sources](/sources/index.md)\n"
            f"- [Entities](/entities/index.md)\n"
            f"- [Concepts](/concepts/index.md)\n\n"
            "Drop source files into `raw/`, then run INGEST.\n"
        )
        root_index.write_text(
            f"---\ntype: Index\ntitle: {args.title}\ntimestamp: {ts}\n---\n\n{section_links}",
            encoding="utf-8",
        )

    log = root / "log.md"
    if not log.exists():
        log.write_text(f"# Log\n\n- {ts} — bundle initialized.\n", encoding="utf-8")

    (root / "raw" / ".gitkeep").write_text("", encoding="utf-8")

    if not args.no_git and not (root / ".git").exists():
        try:
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "-A"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init OKF wiki"], cwd=root, check=False)
        except Exception as e:
            print(f"(git skipped: {e})")

    print(f"Initialized OKF wiki at {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
