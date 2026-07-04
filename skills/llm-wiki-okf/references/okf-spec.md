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

## Reserved filenames

- `index.md` — directory overview. Read this first when navigating.
- `log.md` — change history. Newest entries first.

These are not concepts and do not require `type`. `index.md` may include `type: Index` for consistency; `log.md` should not have frontmatter.

## Conformance checklist

- UTF-8 markdown files.
- Every concept has frontmatter with `type`.
- Reserved fields use the reserved names; `timestamp` is valid ISO 8601.
- Every `.md` cross-link resolves to an existing file.
- `index.md`/`log.md` follow the reserved meaning.
- Frontmatter uses only the supported yamlish subset (run `okf_lint.py --strict-frontmatter` to verify).
