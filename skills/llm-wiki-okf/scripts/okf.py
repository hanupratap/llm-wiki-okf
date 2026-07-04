#!/usr/bin/env python3
"""Unified CLI for llm-wiki-okf — dispatches to per-operation scripts. Stdlib only."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

SUBCOMMAND_MAP: dict[str, tuple[str, list[str]]] = {
    "init": ("okf_init.py", []),
    "ingest": ("okf_ingest.py", []),
    "update": ("okf_update.py", []),
    "truth": ("okf_update.py", ["--truth"]),
    "archive": ("okf_archive.py", []),
    "diff": ("okf_diff.py", []),
    "lint": ("okf_lint.py", []),
    "search": ("okf_search.py", []),
    "status": ("okf_status.py", []),
    "index": ("okf_index.py", []),
    "now": ("okf_now.py", []),
    "dir": ("okf_dir.py", []),
    "wire": ("okf_wire.py", []),
}

HELP = """llm-wiki-okf — persistent markdown knowledge base

Usage: okf <subcommand> [flags]

Subcommands:
  init <bundle>          Scaffold a new wiki bundle
  ingest <source>        Ingest a raw source document
  update <page>          Bump timestamp + log after edit
  truth <page>           Atomic rewrite: read new body from stdin
  archive <page>         Archive a page (set status=archived)
  diff <page>            Show git diff for a page
  lint <bundle>          Validate format and links
  search <query>         Ranked search across pages
  status                 Bundle health overview
  index <bundle>         Regenerate indexes
  now                    Print current ISO 8601 timestamp
  dir                    Show resolved bundle directories
  wire --agent <name>    Idempotent agent-config wiring

See full docs: https://github.com/hanupratap/llm-wiki-okf
"""


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(HELP)
        return 0

    sub = sys.argv[1]
    rest = sys.argv[2:]

    if sub not in SUBCOMMAND_MAP:
        print(f"unknown subcommand: {sub!r}", file=sys.stderr)
        print(file=sys.stderr)
        print(HELP, file=sys.stderr)
        return 1

    script_name, extra_flags = SUBCOMMAND_MAP[sub]
    script_path = SCRIPTS_DIR / script_name

    if not script_path.exists():
        print(f"script not found: {script_path}", file=sys.stderr)
        return 1

    # Ensure the scripts directory is on sys.path for cross-imports
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))

    new_argv = [str(script_path)] + extra_flags + rest

    spec = importlib.util.spec_from_file_location(
        script_name.replace(".py", ""), script_path
    )
    if spec is None or spec.loader is None:
        print(f"could not load {script_path}", file=sys.stderr)
        return 1

    module = importlib.util.module_from_spec(spec)
    orig_argv = sys.argv
    sys.argv = new_argv

    try:
        spec.loader.exec_module(module)
        if hasattr(module, "main"):
            return module.main()
        return 0
    except SystemExit as e:
        return e.code if e.code is not None else 0
    finally:
        sys.argv = orig_argv


if __name__ == "__main__":
    sys.exit(main())
