#!/usr/bin/env python3
"""Update a page's timestamp and log entry after a content change. Stdlib only."""
from __future__ import annotations

import argparse
import os as _os
import subprocess
import sys
from pathlib import Path

from okf_common import bump_timestamp, now_iso, resolve_single_bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="Update a page in an OKF bundle")
    ap.add_argument("page", help="Path to the page file (absolute or bundle-relative)")
    ap.add_argument("--bundle", default=None, help="Bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--message", default=None, help="Log message override")
    ap.add_argument("--no-commit", action="store_true", help="Skip git commit")
    ap.add_argument("--no-lint", action="store_true", help="Skip lint step")
    ap.add_argument("--no-timestamp", action="store_true", help="Skip timestamp bump")
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

    # 1. Bump timestamp
    ts = now_iso()
    if not args.no_timestamp:
        bump_timestamp(page_path)
        print(f"Bumped timestamp: {page_rel}")
    else:
        print(f"Timestamp unchanged: {page_rel}")

    # 2. Append to log.md
    log_path = root / "log.md"
    if not log_path.exists():
        log_path.write_text(f"# Log\n\n", encoding="utf-8")
    log_content = log_path.read_text(encoding="utf-8", errors="replace")
    msg = args.message or f"update: {page_rel}"
    entry = f"- {ts} — {msg}\n"
    if "# Log" in log_content:
        parts = log_content.split("\n", 1)
        log_content = parts[0] + "\n\n" + entry + (parts[1] if len(parts) > 1 else "")
    else:
        log_content = f"# Log\n\n" + entry + log_content
    log_path.write_text(log_content, encoding="utf-8")
    print(f"Updated log.md")

    # 3. Rebuild indexes
    from okf_index import main as index_main  # noqa: E402
    sys.argv = ["okf_index.py", str(root)]
    index_main()
    sys.argv = ["okf_update.py"]

    # 4. Lint
    if not args.no_lint:
        from okf_lint import main as lint_main  # noqa: E402
        sys.argv = ["okf_lint.py", str(root)]
        rc = lint_main()
        sys.argv = ["okf_update.py"]
        if rc != 0:
            print("Lint errors found — fix them before committing.", file=sys.stderr)

    # 5. Commit
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
