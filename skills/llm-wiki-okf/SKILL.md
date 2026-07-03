---
name: llm-wiki-okf
description: >-
  Persistent markdown knowledge base (OKF format) for LLM project memory.
  Use whenever the user or project has documented facts — architecture,
  design decisions, domain entities, datasets — that must be consulted
  before answering, even if the user doesn't mention the wiki explicitly.
  Also use when ingesting raw documents into a project or personal wiki,
  updating pages after a source changes, or linting a bundle. Trigger on
  phrases like "remember this", "what do we know about X", "add to the
  wiki", "update the wiki", "what did we decide about...", or any question
  about prior project decisions or recorded knowledge.
---

# LLM Wiki (OKF-light)

Persistent markdown knowledge base with two layers:
- `raw/` — immutable source documents. Read only.
- `*.md` — LLM-generated concept pages, one idea per file.

Full format reference: [references/okf-spec.md](references/okf-spec.md).

## When to use

- The user asks about recorded facts: the project, its architecture, domain entities, tools, or prior decisions.
- You are about to ingest a raw source into a local or global wiki.
- You need to update wiki pages after a raw source changes.
- You need to lint a wiki for format or link errors.

## Query-first (non-negotiable)

**`index.md` is the mandatory entry point for every query — no exceptions.** Never answer a
memory question from raw files, project files, or external sources before the wiki has been
consulted through its index.

1. Determine scope. Default bundle is `~/.llm-wiki`; per-project bundles live in `./.llm-wiki`.
   Follow `AGENTS.md` routing if present (query both global + local tiers when unsure).
2. **Read `index.md` first. Always.** Even if it looks short, or its `<!-- okf:auto-index -->`
   section is empty.
3. **Follow the section links listed in `index.md`** — `/notes/index.md`, `/sources/index.md`,
   `/entities/index.md`, `/concepts/index.md`. Subsection indexes list the actual pages.
4. Read the relevant pages from those subsection indexes. Grep the bundle if a topic is not
   surfaced by any index.
5. Cite by path: `per /notes/project-overview.md`, or with tier label
   `per global /entities/hanupratap-singh-chauhan.md` / `per local /notes/...`.
6. Only after the wiki is silent or confidence is low, fall back to `raw/` then external sources.

Common failure modes to avoid:
- Skipping the wiki and reading project / raw files directly.
- Reading only the top-level `index.md`, seeing an empty auto-index, and concluding the wiki is empty.
- Answering from memory of a prior turn instead of re-reading the cited page.

## Operations

All `scripts/okf_*.py` paths below are relative to this skill's directory (the folder containing this `SKILL.md`). Resolve them from there, not from the current working directory.

### INIT
Scaffold a new wiki bundle:
```bash
python3 scripts/okf_init.py <bundle>
```

This creates the `raw/`, `sources/`, `notes/`, `entities/`, and `concepts/` directories plus initial index files.

### INGEST
Add a new raw source to the wiki:

1. Drop the file into `raw/<file>` (e.g., `raw/design-doc.md`).
2. Read the source and write a summary to `sources/<slug>.md` with `type: Source`, `sources: [raw/<file>]`, `timestamp`.
3. Grep affected pages; re-read the raw source; make surgical edits to existing pages.
4. Create new `Note` pages for new concepts, linking each to at least one existing page.
5. Update indexes:
   ```bash
   python3 scripts/okf_index.py <bundle>
   ```
6. Append to `log.md`.
7. Lint:
   ```bash
   python3 scripts/okf_lint.py <bundle>
   ```
8. Commit:
   ```bash
   git -C <bundle> add -A
   git -C <bundle> commit -m "ingest: <slug>"
   ```

If a new source contradicts an existing page, flag it and ask before resolving.

### UPDATE
After a raw source changes:

1. Grep affected pages.
2. Re-read the raw source for the changed fact.
3. For meaning changes, show a diff and ask before applying.
4. Surgical edit; update `sources` and bump `timestamp`.
5. Update indexes:
   ```bash
   python3 scripts/okf_index.py <bundle>
   ```
6. Append to `log.md`.
7. Lint:
   ```bash
   python3 scripts/okf_lint.py <bundle>
   ```
8. Commit:
   ```bash
   git -C <bundle> add -A
   git -C <bundle> commit -m "update: <slug>"
   ```

### LINT
```bash
python3 scripts/okf_lint.py <bundle>
```

Fix errors immediately; treat warnings as real problems.

## Format essentials

- `type` is required on every concept page: `Source`, `Note`, `Index`.
- `sources` is required on factual pages (`Source`, `Note`). Must point to `raw/<file>` that exists.
- Cross-links are root-relative: `[label](/path/to/file.md)`. Targets must exist. External URLs (`https://...`) are fine and are not checked.
- `index.md` is the directory entry point; `log.md` is the change history.
- Get a fresh timestamp via `python3 scripts/okf_now.py` rather than hand-writing one (avoids bad-timestamp errors).

## Rules

- Compile from `raw/`, not from wiki text.
- Every factual page has `sources`.
- Surgical edits only; do not rewrite whole pages.
- Flag contradictions; do not overwrite silently.
- No orphan pages; every concept page must be linked from at least one non-index page (links from `index.md` do not count).
- Show diff and confirm before meaning changes.
- Commit after every INGEST / UPDATE.
