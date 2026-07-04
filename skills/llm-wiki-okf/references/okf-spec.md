# Open Knowledge Format (OKF) v0.1

OKF is a lightweight format for LLM-readable knowledge bases. It is not a platform or service. A bundle is a directory of markdown files.

## Bundle structure

```
bundle/
├── index.md          # overview
├── log.md            # change history
├── raw/              # source documents (immutable)
└── *.md / subdirs/   # concept pages
```

## Concept files

A concept = YAML frontmatter + markdown body. File path is the concept's identity.

```yaml
---
type: Note
title: Transformer architecture
description: Replaces recurrence with self-attention.
resource: https://example.com/paper
tags: [nlp, architecture]
timestamp: 2026-07-03T14:30:00Z
---
```

## Reserved fields

| Field | Required | Meaning |
|-------|----------|---------|
| `type` | yes | Kind of concept. Producer-defined vocabulary. |
| `title` | no | Human-readable name. |
| `description` | no | One-line summary. |
| `resource` | no | URL to the thing this concept points at. |
| `tags` | no | List of strings. |
| `timestamp` | no | ISO 8601 UTC of last meaningful update. |
| `status` | no | Lifecycle status: `active`, `draft`, or `archived`. |

Rules:
- No `type` = non-conformant.
- Do not use alternative keys for reserved fields. Use `title`, not `name`; `resource`, not `url`; `timestamp`, not `date`/`updated`/`modified`.
- Producers can add extra fields. This skill adds `sources` and optional `confidence`/`lifecycle`.
## Frontmatter syntax (yamlish subset)

The OKF tooling uses a minimal YAML parser that supports a deliberate subset of the YAML spec.
Frontmatter that stays within this subset is guaranteed to parse correctly.

**Supported:**
- `key: value` — plain scalar. Quotes (`"` / `'`) are stripped.
- `key: [a, b, c]` — inline list.
- `key:` followed by indented `- item` lines — block list.

**NOT supported:**
- Nested mappings: `key: { sub: val }` — use top-level flat fields instead.
- Multiline string scalars: `>`, `|` — keep descriptions concise.
- Inline comments after a value: `key: value  # comment` — put comments on their own line starting with `#`.
- Tabs as indentation — use spaces only.
- Quoted keys containing `:` — use unquoted keys.

**Example — valid:**

```yaml
---
type: Source
title: Design document
description: Architecture decisions for the user service
tags: [architecture, decisions]
sources: [raw/design-doc.md]
timestamp: 2026-07-03T14:30:00Z
---
```

**Example — INVALID (nested map, will parse incorrectly or be dropped):**

```yaml
---
type: Note
metadata:
  author: Alice
  version: 2
---
```

When in doubt, run `okf_lint.py --strict-frontmatter` which detects probable parser failures (e.g. empty lists that may indicate dropped nested content).

## Cross-links

Use root-relative markdown links: `[customers](/tables/customers.md)`. Targets must exist. The link graph is the knowledge graph.

## Lifecycle (status)

Pages can carry an optional `status` field:

| Value | Meaning |
|-------|---------|
| `active` | Current knowledge (default when absent) |
| `draft` | Work in progress, not yet reviewed |
| `archived` | Superseded — preserved for history, excluded from search by default |

When a conclusion is overturned, **archive** the old page rather than deleting it.
The `kind: reversal` timeline entry explains why the page was superseded.

`okf_lint.py` treats archived pages as exempt from orphan-link checks (they are
historical), but their outbound links must still resolve.

`okf_search.py` excludes archived pages by default. Use `--include-archived` to
surface them.


## Timeline (per-page provenance)

Pages can carry an optional `## timeline` section after the body. Timeline entries
record why the page's content changed, not just that it changed.

```yaml
## timeline

- time: 2026-07-04T12:00:00Z
  kind: decision
  summary: Switched auth from JWT to session cookies
  source: raw/security-review.md
  affects: [auth-flow]
- time: 2026-07-03T10:00:00Z
  kind: evidence
  summary: Benchmarks confirm 40% latency reduction
```

### Entry fields

| Field | Required | Meaning |
|-------|----------|---------|
| `time` | yes | ISO 8601 timestamp (UTC recommended) |
| `kind` | yes | One of `decision`, `evidence`, `reversal`, `note` |
| `summary` | yes | One-line description of what changed and why |
| `source` | no | Link back to a source in `raw/` that motivated the change |
| `affects` | no | Comma-separated list of related page ids |

### Entry kinds

| Kind | Meaning |
|------|---------|
| `decision` | A deliberate choice or new understanding |
| `evidence` | Data, benchmark, or observation that informed a decision |
| `reversal` | A prior conclusion was overturned (used with `status: archived`) |
| `note` | General annotation — minor clarification or remark |

### Discipline

- Timeline is **append-only**. Existing entries are never edited or reordered.
- Every meaningful rewrite of a page's body should append a `kind: decision` entry.
- Use `okf update --kind <k> --summary "..." <page>` to append surgically.
- Use `okf truth <page> < <new-body.md>` for atomic rewrite + provenance (reads
  new body from stdin, replaces the body section, and appends a `kind: decision`
  entry in one write).
- Use `okf archive <page> --reversal-summary "..."` to archive with explanation.


## Reserved filenames
## Conformance checklist

- UTF-8 markdown files.
- Every concept has frontmatter with `type`.
- Reserved fields use the reserved names; `timestamp` is valid ISO 8601.
- Every `.md` cross-link resolves to an existing file.
- `index.md`/`log.md` follow the reserved meaning.
- `status` is valid (`active`, `draft`, `archived`) or absent.
- Timeline entries (if present) have `time`, `kind`, and `summary` fields.
- Frontmatter uses only the supported yamlish subset (run `okf_lint.py --strict-frontmatter` to verify).
