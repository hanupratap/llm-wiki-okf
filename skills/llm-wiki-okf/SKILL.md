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
   Use `okf_status.py --tier all` for a quick overview of active tiers.
2. **Read `index.md` first. Always.** Even if it looks short, or its `<!-- okf:auto-index -->`
   section is empty.
3. **Follow the section links listed in `index.md`** — `/notes/index.md`, `/sources/index.md`,
   `/entities/index.md`, `/concepts/index.md`. Subsection indexes list the actual pages.
4. If a topic isn't surfaced by the indexes, use **`okf_search.py <query>`** for ranked
   results across concept pages before falling back to raw grep.
5. Cite by path: `per /notes/project-overview.md`, or with tier label
   `per global /entities/hanupratap-singh-chauhan.md` / `per local /notes/...`.
6. Only after the wiki is silent or confidence is low, fall back to `raw/` then external sources.

Common failure modes to avoid:
- Skipping the wiki and reading project / raw files directly.
- Reading only the top-level `index.md`, seeing an empty auto-index, and concluding the wiki is empty.
- Answering from memory of a prior turn instead of re-reading the cited page.
- Grepping the bundle without running `okf_search.py` first — ranked search uses weighted scoring,
  not linear scan.

## Script paths

`okf_*.py` scripts live in two places depending on your platform:

- **Pi / Claude Code**: the scripts are in the skill directory. Run as `python3 scripts/okf_*.py`
  resolved relative to this `SKILL.md`'s folder.
- **Cursor / Copilot / Windsurf**: the scripts were installed to `~/.local/bin`. Run by name:
  `okf_init.py`, `okf_lint.py`, etc. If `scripts/okf_*.py` doesn't resolve, try the bare name.
- The `okf_common.py` module must be co-located with the script being run (same directory as all
  `okf_*.py` files).

## Operations

### SEARCH
Find relevant pages for a query using ranked token scoring:

```bash
python3 scripts/okf_search.py <query> [--tier all|global|local] [--max-results N] [--json]
```

Use this whenever the index path doesn't surface a topic. Searches frontmatter (title, tags,
description) and page body, ranking by relevance.

For a table-of-contents overview of all pages:

```bash
python3 scripts/okf_search.py --toc [--tier all]
```

### STATUS
Quick health overview of one or all tiers:

```bash
python3 scripts/okf_status.py [--tier all|global|local] [--json]
```

Shows page counts by type, number of raw source files, and the last logged change.

### INIT
Scaffold a new wiki bundle:

```bash
python3 scripts/okf_init.py <bundle> [--title "My Wiki"]
```

Use `--from-readme` to infer the title and description from a `README.md` in the current directory:

```bash
python3 scripts/okf_init.py <bundle> --from-readme [--readme-path path/to/README.md]
```

This creates the `raw/`, `sources/`, `notes/`, `entities/`, and `concepts/` directories plus initial index files.

### INGEST
Add a new raw source to the wiki. The script copies the source into `raw/`, creates a skeleton
`source` page with correct frontmatter, updates `log.md`, rebuilds indexes, lints, and commits:

```bash
python3 scripts/okf_ingest.py <source-file> [--title "Title"] [--slug my-slug] [--tier all|global|local] [--no-commit] [--dry-run]
```

After the script runs:

1. Read the source and fill in the skeleton `sources/<slug>.md` page.
2. Grep affected pages; re-read the raw source; make surgical edits to existing pages.
3. Create new `Note` pages for new concepts, linking each to at least one existing page.
4. Run `okf_update.py <page>` on each page you edited to bump timestamps and log.

If a new source contradicts an existing page, use `okf_diff.py <page>` to show the current state,
then flag the contradiction and ask before resolving.

### UPDATE
After editing a page, bump its timestamp, log, re-index, lint, and commit:

```bash
python3 scripts/okf_update.py <page> [--message "custom log message"] [--no-commit]
```

### DIFF
Show a git diff for a page — use this before meaning changes to review what's there:

```bash
python3 scripts/okf_diff.py <page> [--previous N] [--since <commit>]
```

### LINT
```bash
python3 scripts/okf_lint.py <bundle> [--tier all|global|local] [--json] [--strict-frontmatter]
```

Fix errors immediately; treat warnings as real problems.

`--strict-frontmatter` adds warnings when the yamlish parser may have silently dropped
content — useful for catching nested YAML, multiline scalars, or tab-indented lists
that the parser doesn't support.

## Format essentials

- `type` is required on every concept page: `Source`, `Note`, `Index`.
- `sources` is required on factual pages (`Source`, `Note`). Must point to `raw/<file>` that exists.
- Cross-links are root-relative: `[label](/path/to/file.md)`. Targets must exist. External URLs (`https://...`) are fine and are not checked.
- `index.md` is the directory entry point; `log.md` is the change history.
- Get a fresh timestamp via `python3 scripts/okf_now.py` rather than hand-writing one (avoids bad-timestamp errors).
- Frontmatter must use flat `key: value` syntax. Nested maps, multiline scalars (`>`, `|`), and tab indentation are NOT supported by the parser — use inline lists `key: [a, b]` or block lists instead.

## Rules

- Compile from `raw/`, not from wiki text.
- Every factual page has `sources`.
- Surgical edits only; do not rewrite whole pages.
- Flag contradictions; do not overwrite silently.
- No orphan pages; every concept page must be linked from at least one non-index page (links from `index.md` do not count).
- Show diff and confirm before meaning changes.
- Commit after every INGEST / UPDATE.
