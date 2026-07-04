#!/usr/bin/env python3
"""Show a git diff for a page in an OKF bundle. Stdlib only.

Without arguments, shows the most recent commit diff touching the page.
Use --previous N to go further back.
"""
from __future__ import annotations

import argparse
import os as _os
import subprocess
import sys
from pathlib import Path

from okf_common import resolve_single_bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="Show diff for an OKF wiki page")
    ap.add_argument("page", nargs="?", help="Page path (absolute or bundle-relative)")
    ap.add_argument("--bundle", default=None, help="Bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--previous", type=int, default=1,
                    help="Which previous commit to diff against (default: 1)")
    ap.add_argument("--since", default=None,
                    help="Show diff since this commit hash, tag, or date")
    args = ap.parse_args()

    resolved = resolve_single_bundle(args.bundle, args.tier)
    if resolved is None or not resolved[1].is_dir():
        print(f"Bundle not found (tier: {args.tier})", file=sys.stderr)
        return 1
    _, root = resolved

    git_dir = root / ".git"
    if not git_dir.is_dir():
        print(f"No git repo at {root} — diff requires git", file=sys.stderr)
        return 1

    if args.page:
        page_path = Path(args.page)
        if not page_path.is_absolute():
            page_path = (root / args.page).resolve()
        if not page_path.exists():
            print(f"Page not found: {args.page}", file=sys.stderr)
            return 1
        page_rel = _os.path.relpath(_os.path.realpath(page_path), _os.path.realpath(root))
    else:
        # No specific page — show what's changed in the entire bundle
        page_rel = None

    try:
        if args.since:
            # Diff against a specific commit/tag
            cmd = ["git", "-C", str(root), "diff", args.since]
            if page_rel:
                cmd.extend(["--", page_rel])
        elif page_rel is None:
            # Latest commit for whole bundle
            cmd = ["git", "-C", str(root), "log", "-1", "-p"]
        else:
            # Diff against the Nth previous commit touching this page
            # Get the commit hash N steps back
            log_result = subprocess.run(
                ["git", "-C", str(root), "log", f"-{args.previous}",
                 "--format=%H", "--", page_rel],
                capture_output=True, text=True, check=True,
            )
            hashes = log_result.stdout.strip().split("\n")
            hashes = [h for h in hashes if h]
            if not hashes:
                print(f"No git history for {page_rel}")
                return 0

            commit_hash = hashes[-1]  # last entry = Nth from HEAD
            # Get the parent of that commit
            parent_result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", f"{commit_hash}^"],
                capture_output=True, text=True, check=False,
            )
            if parent_result.returncode == 0 and parent_result.stdout.strip():
                parent = parent_result.stdout.strip()
                cmd = ["git", "-C", str(root), "diff", parent, commit_hash, "--", page_rel]
            else:
                # Root commit — show the initial version
                cmd = ["git", "-C", str(root), "show", commit_hash, "--", page_rel]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout.strip():
            print(result.stdout)
        else:
            print(f"(no diff)")

        if result.stderr.strip():
            print(result.stderr, file=sys.stderr)

    except subprocess.CalledProcessError as e:
        print(f"git error: {e}", file=sys.stderr)
        if e.stderr:
            print(e.stderr, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
