#!/usr/bin/env python3
"""Archive a page: set status=archived, append reversal timeline entry. Stdlib only."""
from __future__ import annotations

import argparse
import re
import os as _os
import subprocess
import sys
from pathlib import Path

from okf_common import (
    append_to_section,
    atomic_write_text,
    format_timeline_entry,
    now_iso,
    parse_frontmatter,
    resolve_single_bundle,
)



def _ensure_timeline_section(text: str) -> str:
    """Add a ``## timeline`` section to a page if one doesn't exist."""
    if re.search(r"^##\s+timeline[ \t]*$", text, re.MULTILINE):
        return text
    fm_match = re.match(r"^---\s*\n.*?\n---\s*\n?", text, re.DOTALL)
    if fm_match:
        insert_at = fm_match.end()
        before = text[:insert_at]
        after = text[insert_at:].lstrip()
        return before + "\n\n## timeline\n\n_(no entries yet)_\n" + after
    return text + "\n\n## timeline\n\n_(no entries yet)_\n"

def main() -> int:
    ap = argparse.ArgumentParser(description="Archive an OKF wiki page")
    ap.add_argument("page", help="Page path (absolute or bundle-relative)")
    ap.add_argument("--bundle", default=None, help="Bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--reversal-summary", default=None,
                    help="Explain why this page was overturned (appended as reversal timeline entry)")
    ap.add_argument("--message", default=None, help="Log message override")
    ap.add_argument("--no-commit", action="store_true", help="Skip git commit")
    ap.add_argument("--no-lint", action="store_true", help="Skip lint step")
    args = ap.parse_args()

    resolved = resolve_single_bundle(args.bundle, args.tier)
    if resolved is None or not resolved[1].is_dir():
        print(f"Bundle not found (tier: {args.tier})", file=sys.stderr)
        return 1
    _, root = resolved

    page_path = Path(args.page)
    if not page_path.is_absolute():
        page_path = (root / args.page).resolve()
    if not page_path.exists():
        print(f"Page not found: {args.page}", file=sys.stderr)
        return 1

    page_rel = _os.path.relpath(_os.path.realpath(page_path), _os.path.realpath(root))
    ts = now_iso()

    # Read current page
    text = page_path.read_text(encoding="utf-8", errors="replace")

    # Ensure timeline section exists
    text = _ensure_timeline_section(text)

    # Append reversal timeline entry if summary given
    if args.reversal_summary:
        entry = format_timeline_entry(
            time=ts, kind="reversal",
            summary=args.reversal_summary,
        )
        text = append_to_section(text, "timeline", entry)

    # Set status to archived and bump timestamp in frontmatter
    fm, body = parse_frontmatter(text)
    fm["status"] = "archived"
    fm["timestamp"] = ts
    lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    new_text = "\n".join(lines) + "\n\n" + body.lstrip()

    atomic_write_text(page_path, new_text)
    print(f"Archived: {page_rel}")
    if args.reversal_summary:
        print(f"  reversal: {args.reversal_summary}")

    # Append to log.md
    log_path = root / "log.md"
    if not log_path.exists():
        log_path.write_text("# Log\n\n", encoding="utf-8")
    log_content = log_path.read_text(encoding="utf-8", errors="replace")
    msg = args.message or f"archive: {page_rel}"
    log_entry = f"- {ts} — {msg}\n"
    if "# Log" in log_content:
        parts = log_content.split("\n", 1)
        log_content = parts[0] + "\n\n" + log_entry + (parts[1] if len(parts) > 1 else "")
    else:
        log_content = "# Log\n\n" + log_entry + log_content
    atomic_write_text(log_path, log_content)
    print(f"Updated log.md")

    # Rebuild indexes
    from okf_index import main as index_main
    sys.argv = ["okf_index.py", str(root)]
    index_main()
    sys.argv = ["okf_archive.py"]

    # Lint
    if not args.no_lint:
        from okf_lint import main as lint_main
        sys.argv = ["okf_lint.py", str(root)]
        rc = lint_main()
        sys.argv = ["okf_archive.py"]
        if rc != 0:
            print("Lint errors found — fix them before committing.", file=sys.stderr)

    # Commit
    if not args.no_commit:
        git_dir = root / ".git"
        if git_dir.is_dir():
            try:
                subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
                subprocess.run(
                    ["git", "-C", str(root), "commit", "-m", msg],
                    check=False,
                )
                print(f"Committed: {msg}")
            except subprocess.CalledProcessError as e:
                print(f"(git skipped: {e})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
