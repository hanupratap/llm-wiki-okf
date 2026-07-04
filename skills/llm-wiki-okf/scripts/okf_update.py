#!/usr/bin/env python3
"""Update a page's timestamp and log entry after a content change. Stdlib only."""
from __future__ import annotations

import argparse
import os as _os
import re
import subprocess
import sys
from pathlib import Path

from okf_common import (
    TIMELINE_KINDS,
    _section_range,
    append_to_section,
    atomic_write_text,
    bump_timestamp,
    format_timeline_entry,
    now_iso,
    parse_frontmatter,
    replace_section,
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
    ap = argparse.ArgumentParser(description="Update a page in an OKF bundle")
    ap.add_argument("page", help="Path to the page file (absolute or bundle-relative)")
    ap.add_argument("--bundle", default=None, help="Bundle path")
    ap.add_argument("--tier", default="local", choices=["local", "global", "all"],
                    help="Tier selector (default: local)")
    ap.add_argument("--message", default=None, help="Log message override")
    ap.add_argument("--no-commit", action="store_true", help="Skip git commit")
    ap.add_argument("--no-lint", action="store_true", help="Skip lint step")
    ap.add_argument("--no-timestamp", action="store_true", help="Skip timestamp bump")
    # Timeline flags (Phase 1)
    ap.add_argument("--kind", default=None, choices=TIMELINE_KINDS,
                    help="Timeline entry kind (triggers timeline append)")
    ap.add_argument("--summary", default=None,
                    help="Timeline entry summary (required with --kind)")
    # Atomic truth flag (Phase 2)
    ap.add_argument("--truth", action="store_true",
                    help="Read new page body from stdin and rewrite atomically")
    args = ap.parse_args()

    if args.truth and args.kind:
        ap.error("--truth and --kind are mutually exclusive; --truth implies kind=decision")
    if args.kind and not args.summary:
        ap.error("--summary is required with --kind")

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

    # ── Truth/k timeline operations on the page content ─────────────
    if args.truth or args.kind:
        text = page_path.read_text(encoding="utf-8", errors="replace")

        if args.truth:
            # --truth: read new body from stdin, replace body section,
            # append kind=decision timeline entry, all atomically
            new_body = sys.stdin.read().strip()
            if not new_body:
                print("--truth reads new body from stdin, but stdin was empty", file=sys.stderr)
                return 1

            text = _ensure_timeline_section(text)
            text = replace_section(text, "body", new_body)
            entry = format_timeline_entry(
                time=ts, kind="decision",
                summary=args.summary or "Rewrote page body",
            )
            text = append_to_section(text, "timeline", entry)

            print(f"Rewrote body + appended timeline entry to: {page_rel}")

        else:
            # --kind --summary: append a timeline entry
            text = _ensure_timeline_section(text)
            entry = format_timeline_entry(
                time=ts, kind=args.kind,
                summary=args.summary,
            )
            text = append_to_section(text, "timeline", entry)
            print(f"Appended {args.kind} timeline entry to: {page_rel}")
            print(f"  summary: {args.summary}")

        # Bump frontmatter timestamp
        fm, body = parse_frontmatter(text)
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
        args.no_timestamp = True  # already bumped above

    # ── 1. Bump timestamp (if not already done above) ─────────
    if not args.no_timestamp:
        bump_timestamp(page_path)
        print(f"Bumped timestamp: {page_rel}")
    elif not args.truth and not args.kind:
        print(f"Timestamp unchanged: {page_rel}")

    # ── 2. Append to log.md ───────────────────────────────────
    log_path = root / "log.md"
    if not log_path.exists():
        log_path.write_text("# Log\n\n", encoding="utf-8")
    log_content = log_path.read_text(encoding="utf-8", errors="replace")
    msg = args.message or f"update: {page_rel}"
    log_entry = f"- {ts} — {msg}\n"
    if "# Log" in log_content:
        parts = log_content.split("\n", 1)
        log_content = parts[0] + "\n\n" + log_entry + (parts[1] if len(parts) > 1 else "")
    else:
        log_content = "# Log\n\n" + log_entry + log_content
    atomic_write_text(log_path, log_content)
    print(f"Updated log.md")

    # ── 3. Rebuild indexes ───────────────────────────────────
    from okf_index import main as index_main
    sys.argv = ["okf_index.py", str(root)]
    index_main()
    sys.argv = ["okf_update.py"]

    # ── 4. Lint ──────────────────────────────────────────────
    if not args.no_lint:
        from okf_lint import main as lint_main
        sys.argv = ["okf_lint.py", str(root)]
        rc = lint_main()
        sys.argv = ["okf_update.py"]
        if rc != 0:
            print("Lint errors found — fix them before committing.", file=sys.stderr)

    # ── 5. Commit ────────────────────────────────────────────
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
