#!/usr/bin/env bash
set -euo pipefail

# llm-wiki-okf multi-platform installer
# Repo: https://github.com/hanupratap/llm-wiki-okf

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

success() { echo -e "${GREEN}✓${NC} $1"; }
warn()    { echo -e "${YELLOW}!${NC} $1"; }
fail()    { echo -e "${RED}✗${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$SCRIPT_DIR/skills/llm-wiki-okf"

# Determine where this script is running from (git clone, npm global, etc.)
find_skill_dir() {
  if [ -d "$SKILL_DIR" ]; then
    echo "$SKILL_DIR"
  elif [ -f "$SCRIPT_DIR/SKILL.md" ]; then
    echo "$SCRIPT_DIR"
  else
    # Try npm global install
    local npm_root
    npm_root="$(npm root -g 2>/dev/null || echo "")"
    if [ -n "$npm_root" ] && [ -d "$npm_root/llm-wiki-okf/skills/llm-wiki-okf" ]; then
      echo "$npm_root/llm-wiki-okf/skills/llm-wiki-okf"
    elif [ -d "$npm_root/llm-wiki-okf" ] && [ -f "$npm_root/llm-wiki-okf/SKILL.md" ]; then
      echo "$npm_root/llm-wiki-okf"
    else
      echo ""
    fi
  fi
}

install_scripts() {
  local skill_dir="$1"
  local bin_dir="${HOME}/.local/bin"

  mkdir -p "$bin_dir"

  for script in "$skill_dir/scripts/okf_"*.py; do
    local name
    name="$(basename "$script")"
    cp "$script" "$bin_dir/$name"
    chmod +x "$bin_dir/$name"
    success "Installed $name → $bin_dir/$name"
  done

  # Make common module accessible
  if [ -f "$skill_dir/scripts/okf_common.py" ]; then
    cp "$skill_dir/scripts/okf_common.py" "$bin_dir/okf_common.py"
  fi

  # Check if ~/.local/bin is in PATH
  if ! echo "$PATH" | tr ':' '\n' | grep -qF "$bin_dir"; then
    warn "$bin_dir is not in your PATH. Add this to your shell config:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
}

# ─── Installers ───────────────────────────────────────────────

install_claude() {
  local skill_dir="$1"
  local dest="$HOME/.claude/skills/llm-wiki-okf"

  mkdir -p "$dest"
  cp "$skill_dir/SKILL.md" "$dest/"
  cp -r "$skill_dir/scripts" "$dest/" 2>/dev/null || true
  cp -r "$skill_dir/references" "$dest/" 2>/dev/null || true

  success "Claude Code skill installed → $dest"
  echo "  Trigger in Claude: /skill:llm-wiki-okf"
}

install_pi() {
  if command -v pi &>/dev/null; then
    # Try npm install first; fall back to local path
    if pi install npm:llm-wiki-okf 2>/dev/null; then
      success "Pi package installed from npm"
    else
      pi install "$SCRIPT_DIR"
      success "Pi package installed from local path"
    fi
  else
    warn "pi CLI not found. Install it first: https://pi.dev"
    echo "  Then run: pi install npm:llm-wiki-okf"
  fi
}

install_cursor() {
  local skill_dir="$1"
  local dest=".cursor/rules/llm-wiki-okf.md"

  mkdir -p "$(dirname "$dest")"

  cat > "$dest" <<'HEADER'
---
description: Persistent markdown knowledge base (OKF) for project memory
globs: **/*
alwaysApply: false
---

HEADER

  # Extract the core instructions (skip YAML frontmatter)
  sed -n '/^---$/,/^---$/!p' "$skill_dir/SKILL.md" | tail -n +2 >> "$dest"

  success "Cursor rules installed → $dest"
  echo "  Enable in Cursor: Settings → Rules → llm-wiki-okf"
}

install_copilot() {
  local skill_dir="$1"
  local dest=".github/copilot-instructions.md"

  mkdir -p "$(dirname "$dest")"

  if [ -f "$dest" ]; then
    echo "" >> "$dest"
    echo "<!-- llm-wiki-okf rules below -->" >> "$dest"
    echo "" >> "$dest"
  fi

  # Condensed version for Copilot — updated with new scripts
  cat >> "$dest" <<'COPILOT'
## Project Memory (llm-wiki-okf)

This project uses `llm-wiki-okf` for persistent knowledge:

- **Always check `.llm-wiki/index.md` first** before answering questions about
  architecture, design decisions, entities, or domain concepts.
- Follow index → subsection index → concept page, every time.
- Do not answer from raw project files or memory before consulting the wiki.
- Cite using paths: `per .llm-wiki/notes/architecture.md`
- New knowledge goes into the wiki via INGEST command.
- Use `okf_search.py <query>` for ranked retrieval when the index path misses a topic.

Scripts are available (run by name — they are on PATH):
- `okf_init.py <bundle>` — scaffold a new wiki
- `okf_ingest.py <source> [--title ...]` — ingest a raw source
- `okf_search.py <query>` — ranked search across pages
- `okf_update.py <page>` — bump timestamp + log after editing
- `okf_diff.py <page>` — show git diff before changes
- `okf_status.py` — bundle health overview
- `okf_lint.py <bundle>` — validate format and links
- `okf_index.py <bundle>` — regenerate indexes

See https://github.com/hanupratap/llm-wiki-okf for full documentation.
COPILOT

  success "Copilot instructions → $dest"
}

install_windsurf() {
  local skill_dir="$1"
  local dest=".windsurfrules"

  # Append to existing rules if present
  if [ -f "$dest" ]; then
    echo "" >> "$dest"
    echo "<!-- llm-wiki-okf rules below -->" >> "$dest"
  fi

  cat >> "$dest" <<'WINDSURF'
## llm-wiki-okf

Before answering questions about project architecture, design decisions, entities,
or domain concepts, consult `.llm-wiki/index.md` first. Follow index → subsection
index → concept page. Cite paths. Never skip the wiki.

Scripts (on PATH): `okf_search.py`, `okf_ingest.py`, `okf_update.py`, `okf_diff.py`,
`okf_status.py`, `okf_init.py`, `okf_lint.py`, `okf_index.py`
See: https://github.com/hanupratap/llm-wiki-okf
WINDSURF

  success "Windsurf rules → $dest"
}

install_all() {
  local skill_dir="$1"

  echo ""
  echo "Installing llm-wiki-okf for all detected platforms..."
  echo ""

  # Always install scripts
  install_scripts "$skill_dir"

  # Pi
  if command -v pi &>/dev/null; then
    install_pi
  else
    warn "pi not detected — skipping pi install"
  fi

  # Claude Code
  if [ -d "$HOME/.claude" ]; then
    install_claude "$skill_dir"
  else
    warn "Claude Code not detected — skipping Claude install"
  fi

  # Cursor
  if [ -d ".cursor" ] || command -v cursor &>/dev/null; then
    install_cursor "$skill_dir"
  fi

  # Copilot
  if [ -d ".github" ]; then
    install_copilot "$skill_dir"
  fi
}

# ─── Main ─────────────────────────────────────────────────────

main() {
  local skill_dir
  skill_dir="$(find_skill_dir)"

  if [ -z "$skill_dir" ]; then
    fail "Could not find llm-wiki-okf skill directory.
  Run this from the repo root, or install via npm first:
    npm install -g llm-wiki-okf"
  fi

  echo ""
  echo "llm-wiki-okf installer"
  echo "Skill dir: $skill_dir"
  echo ""

  case "${1:-}" in
    claude|claude-code)
      install_scripts "$skill_dir"
      install_claude "$skill_dir"
      ;;
    pi)
      install_pi
      ;;
    cursor)
      install_scripts "$skill_dir"
      install_cursor "$skill_dir"
      ;;
    copilot|github-copilot)
      install_scripts "$skill_dir"
      install_copilot "$skill_dir"
      ;;
    windsurf)
      install_scripts "$skill_dir"
      install_windsurf "$skill_dir"
      ;;
    scripts|tools)
      install_scripts "$skill_dir"
      ;;
    all)
      install_all "$skill_dir"
      ;;
    *)
      echo "Usage: install.sh {claude|pi|cursor|copilot|windsurf|scripts|all}"
      echo ""
      echo "  claude    Install for Claude Code (~/.claude/skills/)"
      echo "  pi        Install for Pi coding agent (pi install npm:llm-wiki-okf)"
      echo "  cursor    Install as Cursor rules (.cursor/rules/)"
      echo "  copilot   Install as GitHub Copilot instructions (.github/copilot-instructions.md)"
      echo "  windsurf  Install as Windsurf rules (.windsurfrules)"
      echo "  scripts   Install CLI scripts only (~/.local/bin/)"
      echo "  all       Install for all detected platforms"
      echo ""
      exit 1
      ;;
  esac

  echo ""
  success "Done. To test: ask your agent 'what do we know about this project?'"
}

main "$@"
