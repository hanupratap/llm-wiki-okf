# llm-wiki-okf

A pi skill for persistent markdown knowledge base (OKF format) — LLM project memory.

## What it does

Two-tier wiki that keeps your LLM sessions informed about project facts:
- `raw/` — immutable source documents (read only)
- `*.md` — LLM-generated concept pages, one idea per file

The skill enforces **query-first discipline**: every memory question starts from `index.md`, follows links through subsection indexes, and only falls back to raw files when the wiki is silent.

## Operations

- **INIT** — scaffold a new wiki bundle
- **INGEST** — add raw source documents and generate concept pages
- **UPDATE** — surgical edits when sources change (shows diff before applying)
- **LINT** — validate format, check for broken links, orphan pages, missing sources

## Install

```bash
pi install npm:llm-wiki-okf
```

Or clone directly:

```bash
git clone https://github.com/hanupratap/llm-wiki-okf.git
pi install ./llm-wiki-okf
```

## Usage

The skill loads automatically when you ask about project facts, architecture, design decisions, or domain entities. Or invoke explicitly:

```
/skill:llm-wiki-okf
```

Triggers include phrases like "remember this", "what do we know about X", "add to the wiki", "update the wiki", "what did we decide about..."

## Format

Full OKF format reference: [SKILL.md](skills/llm-wiki-okf/references/okf-spec.md)

## License

MIT
