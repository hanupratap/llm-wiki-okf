# llm-wiki-okf

Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern and Google's [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (OKF) specification.

Persistent project memory for AI coding agents. A markdown knowledge base the agent consults before answering.

## Why this exists

AI agents read code well but have no memory. Same question across sessions gets different answers. Existing approaches fail:

**CLAUDE.md / flat context files.** The model has no structure to find what it needs. Files become dumps.

**Vector RAG.** Fuzzy matching returns noise. Good for discovery, bad for authoritative answers. The model may skip the search entirely.

**Platform tools.** Tie you to a service, an API, a format you do not control. Data lives outside the repo.

**Raw context dumps.** Cost tokens, burn cache, and the model skims past unstructured text.

## How this is different

**Query-first discipline.** The skill requires the model to read `index.md` before answering any memory question. It cannot skip the wiki, cannot answer from last-session recall, cannot read project files first. Index to subsection index to concept page, every time. Falls back to raw sources only when the wiki is silent.

**Two-tier architecture.** `raw/` is immutable. Source documents are dropped in and never edited. Concept pages are compiled *from raw*, not from wiki text, preventing drift.

```
bundle/
├── index.md          mandatory entry point
├── log.md            change history, newest first
├── raw/              immutable source documents
├── sources/          summaries of raw documents
├── notes/            decisions, architecture, conventions
├── entities/         people, teams, services, datasets
└── concepts/         domain concepts, one idea per file
```

**Surgical and auditable.** No wholesale rewrites. Every factual page requires a `sources` field tracing back to `raw/`. When a new source contradicts an existing page the skill shows a diff and asks before resolving. No silent overwrites.

**Every page is linked.** No orphan pages. Every concept must be linked from at least one non-index page. The cross-link graph is the knowledge graph.

**Git-native.** Every INGEST and UPDATE creates a commit. Full history, revertible, reviewable.

**Built-in tooling.** `okf_search.py` for ranked page retrieval; `okf_ingest.py` and `okf_update.py` for deterministic source/page workflows; `okf_diff.py` for reviewing changes; `okf_status.py` for bundle health; `okf_lint.py` validates broken links, orphan pages, missing sources, bad timestamps, and contradictions; `okf_index.py` regenerates auto-indexes. Errors are hard stops, not warnings.

**No service dependency.** Markdown files in a directory. Works offline, works with git, lives in your repo or `~/.llm-wiki`.

## Comparison

| | llm-wiki-okf | Vector RAG | Flat context files |
|---|---|---|---|
| Model must consult it | Enforced by skill | Model may skip search | Model may skip file |
| Structured retrieval | Index-driven path | Fuzzy, hit-or-miss | Linear scan |
| Source traceability | Every claim to `raw/` | Chunks lose provenance | None |
| Contradiction detection | Flagged, asks first | Diff noise | Silent overwrites |
| Format validation | Lint tool included | N/A | N/A |
| Works offline | Yes, markdown files | Needs embedding service | Yes |
| Git-friendly | Designed for commits | Vector store not git-able | Merge conflicts |

## Install

### Multi-platform installer

```bash
./install.sh pi        # Pi coding agent
./install.sh claude    # Claude Code
./install.sh cursor    # Cursor IDE
./install.sh copilot   # GitHub Copilot
./install.sh windsurf  # Windsurf IDE
./install.sh all       # All detected platforms
```

### Pi

```bash
pi install npm:llm-wiki-okf
```

From git:

```bash
pi install git:github.com/hanupratap/llm-wiki-okf
```

### Claude Code

```bash
git clone https://github.com/hanupratap/llm-wiki-okf.git ~/.claude/skills/llm-wiki-okf
```

Or via npm:

```bash
npm install -g llm-wiki-okf
ln -s "$(npm root -g)/llm-wiki-okf/skills/llm-wiki-okf" ~/.claude/skills/llm-wiki-okf
```

Trigger in Claude: `/skill:llm-wiki-okf`

### Cursor

```bash
./install.sh cursor
```

Creates `.cursor/rules/llm-wiki-okf.md`. Enable it in Cursor Settings → Rules.

### GitHub Copilot

```bash
./install.sh copilot
```

Appends to `.github/copilot-instructions.md`. Copilot will follow the wiki-first discipline.

### Windsurf

```bash
./install.sh windsurf
```

Writes to `.windsurfrules`.

## Usage

The skill loads automatically on memory-related tasks, or explicitly:

```
/skill:llm-wiki-okf
```

Natural triggers: "remember this", "add to the wiki", "what do we know about X", "what did we decide about", "who is responsible for", "how does Y work".

**Initialize a wiki:**

> Initialize a wiki for this project

**Add knowledge:**

> Add docs/architecture.md to the wiki

The model ingests into `raw/`, generates concept pages, updates indexes, lints, and commits.

**Query:**

> What database does the user service use?

The model reads `index.md`, follows links, finds the entity page, answers with citation (`/notes/infrastructure.md`). If the index path misses a topic, use `okf_search.py` for ranked retrieval instead of raw grep.

## Commands

Scripts are in `skills/llm-wiki-okf/scripts/` (Pi / Claude) or on `~/.local/bin` after running `install.sh` (Cursor / Copilot / Windsurf).

```bash
okf_init.py <bundle> [--title ...] [--from-readme]
okf_ingest.py <source> --bundle <bundle> [--title ...] [--slug ...]
okf_update.py <page> --bundle <bundle> [--message ...]
okf_search.py <query> --bundle <bundle> [--tier all|global|local] [--max-results N]
okf_status.py --bundle <bundle> [--tier all|global|local] [--json]
okf_diff.py <page> --bundle <bundle> [--previous N]
okf_lint.py <bundle> [--tier all|global|local] [--strict-frontmatter]
okf_index.py <bundle> [--dry-run]
```

Tiers: `--tier all` queries both the global `~/.llm-wiki` and the per-project `./.llm-wiki` bundles in one pass.

## Testing

Run the stdlib-only test suite:

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
