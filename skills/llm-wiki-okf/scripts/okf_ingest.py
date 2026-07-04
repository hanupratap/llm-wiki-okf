#!/usr/bin/env python3
"""Ingest a raw source into an OKF bundle. Stdlib only.

Creates the raw/ copy, scaffolds a sources/<slug>.md skeleton page with
correct frontmatter, appends to log.md, rebuilds indexes, and lints.
Optionally commits via git.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from okf_common import MARKER, MARKER_CLOSE, now_iso, resolve_single_bundle, slugify


def main() -> int:
    ap = argparse.ArgumentParser(description="Ingest a source into an OKF bundle")
    ap.add_argument("source", help="Path to the source file to ingest")
    ap.add_argument("--bundle", default=None, help="Bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--title", default=None, help="Source title")
    ap.add_argument("--slug", default=None, help="Source slug (auto from title/filename)")
    ap.add_argument("--no-commit", action="store_true", help="Skip git commit")
    ap.add_argument("--no-lint", action="store_true", help="Skip lint step")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen")
    args = ap.parse_args()

    resolved = resolve_single_bundle(args.bundle, args.tier)
    if resolved is None or not resolved[1].is_dir():
        print(f"Bundle not found (tier: {args.tier})", file=sys.stderr)
        return 1
    _, root = resolved

    source_path = Path(args.source).resolve()
    if not source_path.exists():
        print(f"Source not found: {args.source}", file=sys.stderr)
        return 1

    # Derive title and slug
    title = args.title or source_path.stem.replace("-", " ").replace("_", " ").title()
    slug = args.slug or slugify(title) or slugify(source_path.stem)
    ts = now_iso()

    # Destination in raw/
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dest_name = source_path.name
    raw_dest = raw_dir / dest_name
    raw_rel = f"raw/{dest_name}"

    # Source page path
    sources_dir = root / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    source_page = sources_dir / f"{slug}.md"

    if args.dry_run:
        print(f"[dry-run] copy {source_path} → {raw_dest}")
        print(f"[dry-run] create {source_page}")
        print(f"[dry-run] title: {title}")
        print(f"[dry-run] slug: {slug}")
        return 0

    # 1. Copy source to raw/
    shutil.copy2(source_path, raw_dest)
    print(f"Copied  {source_path}  →  {raw_rel}")

    # 2. Write skeleton source page
    frontmatter = (
        f"---\n"
        f"type: Source\n"
        f"title: {title}\n"
        f"sources: [{raw_rel}]\n"
        f"timestamp: {ts}\n"
        f"---\n\n"
        f"# {title}\n\n"
        f"> Source: `{raw_rel}`\n\n"
        f"_Skeleton page — read the source and fill in a summary._\n"
    )
    source_page.write_text(frontmatter, encoding="utf-8")
    print(f"Created {source_page.relative_to(root)}")

    # 3. Append to log.md
    log_path = root / "log.md"
    if not log_path.exists():
        log_path.write_text(f"# Log\n\n", encoding="utf-8")
    log_content = log_path.read_text(encoding="utf-8", errors="replace")
    # Insert after the `# Log` header, before any other content
    entry = f"- {ts} — ingest: {slug} ({raw_rel})\n"
    if "# Log" in log_content:
        parts = log_content.split("\n", 1)
        log_content = parts[0] + "\n\n" + entry + (parts[1] if len(parts) > 1 else "")
    else:
        log_content = f"# Log\n\n" + entry + log_content
    log_path.write_text(log_content, encoding="utf-8")
    print(f"Updated log.md")

    # 4. Rebuild indexes
    from okf_index import main as index_main
    sys.argv = ["okf_index.py", str(root)]
    index_main()
    sys.argv = ["okf_ingest.py"]  # restore

    # 5. Lint
    if not args.no_lint:
        from okf_lint import main as lint_main
        sys.argv = ["okf_lint.py", str(root)]
        rc = lint_main()
        sys.argv = ["okf_ingest.py"]
        if rc != 0:
            print("Lint errors found — fix them before committing.", file=sys.stderr)

    # 6. Commit
    if not args.no_commit:
        git_dir = root / ".git"
        if git_dir.is_dir():
            try:
                subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
                subprocess.run(
                    ["git", "-C", str(root), "commit", "-m", f"ingest: {slug}"],
                    check=False,
                )
                print(f"Committed: ingest: {slug}")
            except subprocess.CalledProcessError as e:
                print(f"(git skipped: {e})")

    print(f"\nDone. Source: {raw_rel}  Page: sources/{slug}.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
