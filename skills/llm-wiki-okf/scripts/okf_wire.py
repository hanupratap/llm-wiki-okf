#!/usr/bin/env python3
"""Idempotent agent-config wiring for llm-wiki-okf. Stdlib only."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

WIRE_BEGIN = "<!-- BEGIN okf -->"
WIRE_END = "<!-- END okf -->"

AGENT_TARGETS: dict[str, str] = {
    "claude": "CLAUDE.md",
    "codex": "AGENTS.md",
    "cursor": ".cursor/rules/llm-wiki-okf.md",
    "copilot": ".github/copilot-instructions.md",
    "windsurf": ".windsurfrules",
}

WIRE_BLOCKS: dict[str, str] = {
    "cursor": """---
description: Persistent markdown knowledge base (OKF) for project memory
globs: **/*
alwaysApply: false
---

{WIRE_BEGIN}
Always consult `.llm-wiki/index.md` before answering questions about project architecture, design decisions, entities, or domain concepts.

Scripts (on PATH): `okf_search.py`, `okf_ingest.py`, `okf_update.py`, `okf_diff.py`, `okf_status.py`, `okf_init.py`, `okf_lint.py`, `okf_index.py`
{WIRE_END}
""",
    "copilot": """{WIRE_BEGIN}
## Project Memory (llm-wiki-okf)

This project uses `llm-wiki-okf` for persistent knowledge:
- Always check `.llm-wiki/index.md` first before answering questions about architecture, design decisions, entities, or domain concepts.
- Follow index to subsection index to concept page, every time.
- Cite using paths: `per .llm-wiki/notes/architecture.md`
- New knowledge goes into the wiki via INGEST command.
- Use `okf_search.py <query>` for ranked retrieval when the index path misses a topic.
- Scripts: `okf_init.py`, `okf_ingest.py`, `okf_search.py`, `okf_update.py`, `okf_diff.py`, `okf_status.py`, `okf_lint.py`, `okf_index.py`
{WIRE_END}
""",
    "windsurf": """{WIRE_BEGIN}
Before answering questions about project architecture, design decisions, entities, or domain concepts, consult `.llm-wiki/index.md` first. Follow index to subsection index to concept page. Cite paths. Never skip the wiki.

Scripts (on PATH): `okf_search.py`, `okf_ingest.py`, `okf_update.py`, `okf_diff.py`, `okf_status.py`, `okf_init.py`, `okf_lint.py`, `okf_index.py`
{WIRE_END}
""",
    "claude": """{WIRE_BEGIN}
## Project Memory (llm-wiki-okf)

This project uses `llm-wiki-okf` for persistent knowledge. Consult `.llm-wiki/index.md` before answering questions about project architecture, design decisions, entities, or domain concepts. See skills/llm-wiki-okf/SKILL.md for the full protocol.
{WIRE_END}
""",
    "codex": """{WIRE_BEGIN}
## Project Memory (llm-wiki-okf)

This project uses `llm-wiki-okf` for persistent knowledge. Consult `.llm-wiki/index.md` before answering questions about project architecture, design decisions, entities, or domain concepts. See skills/llm-wiki-okf/SKILL.md for the full protocol.
{WIRE_END}
""",
}


def _apply_block(path: Path, block: str) -> str:
    """Apply the block to a config file, returning a description of the action."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{block}\n", encoding="utf-8")
        return "created"

    current = path.read_text(encoding="utf-8")
    pattern = re.escape(WIRE_BEGIN) + r"[\s\S]*?" + re.escape(WIRE_END)

    if re.search(pattern, current):
        new_text = re.sub(pattern, block, current)
        if new_text != current:
            path.write_text(new_text, encoding="utf-8")
            return "replaced existing block"
        return "no change (identical)"

    # Append with leading blank lines
    suffix = ("\n" if current.endswith("\n") else "\n\n") + f"{block}\n"
    path.write_text(current + suffix, encoding="utf-8")
    return "appended"


def main() -> int:
    ap = argparse.ArgumentParser(description="Wire llm-wiki-okf into agent config files")
    ap.add_argument("--agent", required=True, nargs="+",
                    choices=list(AGENT_TARGETS.keys()) + ["all"],
                    help="Target agent(s)")
    args = ap.parse_args()

    agents: set[str] = set()
    for a in args.agent:
        if a == "all":
            agents.update(k for k in AGENT_TARGETS)
        else:
            agents.add(a)

    for agent in sorted(agents):
        target = AGENT_TARGETS[agent]
        path = Path(target)

        block_template = WIRE_BLOCKS.get(agent)
        if not block_template:
            print(f"no wire block defined for {agent}", file=sys.stderr)
            continue

        block = block_template.replace("{WIRE_BEGIN}", WIRE_BEGIN).replace(
            "{WIRE_END}", WIRE_END
        )
        action = _apply_block(path, block)
        print(f"[{agent}] {action}: {target}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
