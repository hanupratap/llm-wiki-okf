# llm-wiki-okf

> Inspired by [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern and Google's [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (OKF) specification.

Persistent project memory for your AI coding agent — a markdown knowledge base that your LLM actually consults before answering.

## The problem

AI coding agents are great at reading code, but they have no memory. Ask the same question in two sessions and you get two different answers. Tell them "remember this architecture decision" and… they forget. Other approaches fail in predictable ways:

- **Scatter-shot files** ("just write it in CLAUDE.md") — the model has no structured way to find what it needs, and the file becomes an unreadable dump.
- **RAG / vector search** — fuzzy semantic matching returns noise. Good for discovery, terrible for authoritative answers. The model doesn't *know* to search, and when it does, it often ignores results.
- **Platform-based solutions** — tie you to a service, an API, a format you don't control. Data lives outside your repo.
- **Raw context dumping** — costs tokens, burns cache, and the model skims past it when it's not structured for retrieval.

## What llm-wiki-okf does differently

### Query-first, always

The skill enforces a non-negotiable rule: **before answering any memory question, the model must read `index.md`**. It can't skip the wiki and go straight to project files. It can't answer from last-session memory. It must follow the index → subsection index → concept page chain every time. If the wiki is silent, only then does it fall back to raw sources.

This eliminates the most common failure mode: the LLM having the right information available but never looking at it.

### Two-tier architecture

```
bundle/
├── index.md            ← mandatory entry point, auto-generated index
├── log.md              ← every change, newest first
├── raw/                ← immutable source documents (never edited)
│   └── design-doc.md
├── sources/            ← summaries of raw documents
├── notes/              ← decisions, architecture, conventions
├── entities/           ← people, teams, services, datasets
└── concepts/           ← domain concepts, one idea per file
```

- **`raw/` is immutable.** Source documents are dropped in and never changed. Concept pages are *compiled from raw*, not from wiki text — preventing drift between the source and the summary.
- **One idea per file.** Every concept page has a clear `type`, required `sources`, root-relative cross-links, and a timestamp. The link graph *is* the knowledge graph.

### Surgical, auditable, traceable

| Rule | Why |
|------|-----|
| **Surgical edits only** | No wholesale rewrites. Change what changed, leave the rest intact. |
| **Every factual page has `sources`** | You can always trace a claim back to its origin in `raw/`. |
| **Contradiction flagging** | New source contradicts existing page? The skill shows a diff and *asks before resolving*. No silent overwrites. |
| **No orphan pages** | Every concept must be linked from at least one non-index page. Nothing gets lost in a dead-end file. |
| **Git-committed after every operation** | Every INGEST and UPDATE creates a commit. Full history, revertible, reviewable. |

### Built-in tooling

```
python3 scripts/okf_init.py <bundle>    # scaffold a new wiki
python3 scripts/okf_index.py <bundle>   # regenerate auto-indexes
python3 scripts/okf_lint.py <bundle>    # validate: broken links, orphans, missing sources, bad timestamps
python3 scripts/okf_now.py              # timestamp helper
```

The linter catches format errors, broken cross-links, orphan pages, and missing source references before they become problems.

### Not a platform, not a database

The wiki is just markdown files in a directory. It lives in your project repo or in `~/.llm-wiki`. It works with git. No API keys, no vector database, no service dependency. You own the data.

### LLM-native format

The [OKF format](skills/llm-wiki-okf/references/okf-spec.md) (Open Knowledge Format) is designed for LLM consumption, not human browsing:

- Short files with clear `type` and `description` fields the model can scan quickly
- Index-driven navigation (the model reads the index, follows links, finds the relevant page)
- Root-relative markdown links create a traversable knowledge graph
- YAML frontmatter with reserved fields — no ambiguity about what `title` vs `name` means

## Install

```bash
pi install npm:llm-wiki-okf
```

Or from git:

```bash
pi install git:github.com/hanupratap/llm-wiki-okf
```

## Usage

The skill loads automatically when you talk about project facts. Or invoke it explicitly:

```
/skill:llm-wiki-okf
```

**Natural triggers** — the skill activates on phrases like:

> "remember this", "add to the wiki", "update the wiki", "what do we know about X",
> "what did we decide about...", "who is responsible for...", "how does Y work"

**Initializing a wiki for your project:**

> "Initialize a wiki for this project"

The model will scaffold the bundle, then you can start ingesting documents and recording decisions.

**Adding knowledge:**

> "Add the design doc in docs/architecture.md to the wiki"

The model ingests it into `raw/`, generates concept pages, updates indexes, lints, and commits.

**Querying:**

> "What database do we use for the user service?"

The model reads `index.md` → follows links → finds the relevant entity/note page → answers with citation (`per /notes/infrastructure.md`).

## How it compares

| | llm-wiki-okf | Vector RAG | Flat context files | VS Code Memory |
|---|---|---|---|---|
| **Model knows to consult it** | ✅ enforced by skill | ❌ model may skip search | ❌ model may skip the file | ⚠️ best-effort |
| **Structured retrieval** | ✅ index → sub-index → page | ⚠️ fuzzy, hit-or-miss | ❌ linear scan | ⚠️ limited |
| **Source traceability** | ✅ every claim backed by `raw/` | ❌ chunks lose provenance | ❌ none | ❌ none |
| **Contradiction detection** | ✅ flagged, asks before overwriting | ❌ diff noise | ❌ silent overwrites | ❌ silent overwrites |
| **Format validation** | ✅ lint tool included | ❌ n/a | ❌ n/a | ❌ n/a |
| **Works offline** | ✅ just markdown files | ❌ needs embedding service | ✅ | ✅ |
| **Git-friendly** | ✅ designed for commits | ❌ vector store not git-able | ⚠️ merge conflicts | ❌ opaque blob |
| **No vendor lock-in** | ✅ open format, plain files | ❌ tied to embedding model | ✅ | ⚠️ VS Code specific |

## License

MIT
