#!/usr/bin/env python3
"""Scaffold a new OKF LLM Wiki bundle. Stdlib only."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

from okf_common import MARKER, MARKER_CLOSE, now_iso


def _infer_from_readme(readme_path: Path) -> tuple[str | None, str | None]:
    """Try to infer a wiki title and a brief description from a README.md.

    Returns (title, description) — either may be None.
    """
    if not readme_path.exists():
        return None, None

    text = readme_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    title = None
    description = None

    for line in lines:
        stripped = line.strip()
        # First h1 heading
        if title is None and stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            continue
        # First non-heading, non-empty, non-badge, non-image paragraph after title
        if title is not None and description is None and stripped and not stripped.startswith("#"):
            # Skip badge lines and image references
            if stripped.startswith("[!") or stripped.startswith("![") or stripped.startswith("<"):
                continue
            desc = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", stripped)
            desc = re.sub(r"\*\*([^*]+)\*\*", r"\1", desc)
            desc = desc.strip().strip(".")
            if len(desc) > 20:
                description = desc[:200]
            break

    return title, description


def main() -> int:
    ap = argparse.ArgumentParser(description="Scaffold an OKF LLM Wiki bundle")
    ap.add_argument("bundle_dir", nargs="?", default=None, help="Bundle directory")
    ap.add_argument("--title", default="Wiki", help="Wiki title")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--from-readme", action="store_true",
                    help="Infer title and seed index from a README.md in cwd")
    ap.add_argument("--readme-path", default="README.md",
                    help="Path to README for --from-readme (default: ./README.md)")
    args = ap.parse_args()

    root = Path(args.bundle_dir).resolve()
    ts = now_iso()

    # Infer from README if requested
    description = None
    if args.from_readme:
        readme_p = Path(args.readme_path).resolve()
        inferred_title, inferred_desc = _infer_from_readme(readme_p)
        if inferred_title:
            args.title = inferred_title
        description = inferred_desc

    for sub in ("raw", "sources", "entities", "concepts", "notes"):
        (root / sub).mkdir(parents=True, exist_ok=True)

    for sub in ("sources", "entities", "concepts", "notes"):
        idx = root / sub / "index.md"
        if not idx.exists():
            title = sub.replace("-", " ").title()
            idx.write_text(
                f"---\ntype: Index\ntitle: {title}\ntimestamp: {ts}\n---\n\n"
                f"# {title}\n\n{MARKER}\n{MARKER_CLOSE}\n",
                encoding="utf-8",
            )

    root_index = root / "index.md"
    if not root_index.exists():
        desc_line = f"\n> {description}\n" if description else "\n"
        section_links = (
            f"# {args.title}\n{desc_line}\n"
            "Sections:\n\n"
            f"- [Notes](/notes/index.md)\n"
            f"- [Sources](/sources/index.md)\n"
            f"- [Entities](/entities/index.md)\n"
            f"- [Concepts](/concepts/index.md)\n\n"
            "Drop source files into `raw/`, then run INGEST.\n"
        )
        root_index.write_text(
            f"---\ntype: Index\ntitle: {args.title}\ntimestamp: {ts}\n---\n\n"
            f"{section_links}",
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
            subprocess.run(
                ["git", "commit", "-q", "-m", "init OKF wiki"],
                cwd=root,
                check=False,
            )
        except Exception as e:
            print(f"(git skipped: {e})")

    print(f"Initialized OKF wiki at {root}")
    print(f"  title: {args.title}")
    if description:
        print(f"  description: {description[:80]}…" if len(description) > 80 else f"  description: {description}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
