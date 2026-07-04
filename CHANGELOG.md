# Changelog

## [1.3.1] - 2026-07-04

### Fixed
- **`okf truth` no longer clobbers frontmatter** — the previous release called
  `replace_section` on the full file text, which dropped `type`, `title`, `sources`.
  Now parses frontmatter first, operates on body only, then reassembles.
- **Timeline section now appended at the END of the page** — the previous
  `_ensure_timeline_section` inserted it right after frontmatter, jumbling structure.
  Replaced with `ensure_timeline_section()` (shared in `okf_common.py`) that appends
  at the end, preserving body content order.
- **`_(no entries yet)_` placeholder removed on first real entry** — new
  `append_timeline_entry()` helper detects and replaces the placeholder.
- **Blank line between body and `## timeline` heading** — `replace_section` now
  inserts `\n\n` before the trailing section instead of `\n`.
- **`okf dir` now accepts `--bundle`** — was inconsistent with every other command
  which all accept `--bundle` for explicit path resolution.

### Changed
- Extracted `ensure_timeline_section()` and `append_timeline_entry()` into
  `okf_common.py` as shared helpers (used by `okf_update` and `okf_archive`).
  Removed the duplicate local `_ensure_timeline_section` from both scripts.



### Added
- **Per-page `## timeline`** — append-only provenance for every concept page.
  Entries record what changed and why (`time`, `kind`, `summary`, optional `source`, `affects`).
  Entry kinds: `decision`, `evidence`, `reversal`, `note`.
- **`okf update --kind` / `--summary`** — append a timeline entry when editing a page.
  If no `## timeline` section exists, one is created automatically.
- **`okf truth`** — atomic page rewrite with provenance: reads new body from stdin,
  replaces the body section, appends a `kind: decision` timeline entry, bumps timestamp,
  reindexes, lints, and commits — all in one atomic write.
- **`okf archive`** — archive a page with optional reversal summary. Sets `status: archived`,
  appends `kind: reversal` timeline entry, preserves full history.
- **`okf status` now reports lifecycle counts** — active/draft/archived page breakdown.
- **`okf search --include-archived`** — shows archived pages (excluded by default).
- **`okf lint` validates timelines** — `bad-timeline-kind` (error), `timeline-out-of-order` (warn),
  `timeline-malformed` (warn). Also checks `bad-status` for invalid status values.
  Archived pages exempt from orphan-link checks.
- **`okf dir`** — show resolved bundle directories with exists/populated/page-count info.
- **`okf wire --agent <name>`** — idempotent agent-config wiring with `<!-- BEGIN okf -->` markers.
- **Unified `okf` CLI** — one entry point for all operations (`okf init`, `okf ingest`, etc.).
  Per-script entry points (`okf_init.py`, etc.) still work.
- **Atomic file writes** — `atomic_write_text()` helper writes via temp-file + replace,
  used by `bump_timestamp()`, `okf_update --truth`, `okf_archive`, and log updates.
- **Section helpers** in `okf_common.py`: `extract_section()`, `replace_section()`,
  `append_to_section()`, `_section_range()`, `format_timeline_entry()`, `_yaml_scalar()`.
- **`LIFECYCLE_STATUSES` and `TIMELINE_KINDS`** constants exported from `okf_common.py`.

### Changed
- **`okf-spec.md`** — added Timeline (per-page provenance) and Lifecycle (status) sections.
- **`SKILL.md`** — restructured with unified CLI commands; added UPDATE (timeline),
  TRUTH, ARCHIVE, DIR, WIRE operations; added provenance/archive rules.
- **`install.sh`** — installs unified `okf` CLI; updated Copilot/Windsurf sections with new commands.
- **`okf_ingest.py`** — skeleton source pages now include a `## timeline` section.

### Deprecated
- Standalone per-script entry points (`okf_lint.py`, `okf_search.py`, etc.) still work
  but the unified `okf <subcommand>` form is preferred for new use.



### Added
- **`okf_search.py`** — ranked stdlib token search across concept pages with weighted frontmatter + body scoring. Supports `--toc` for table-of-contents overview, `--json`, and `--tier all|global|local`.
- **`okf_ingest.py`** — deterministic source ingestion: copies source into `raw/`, scaffolds a `sources/<slug>.md` page with correct frontmatter + timestamp, appends `log.md`, rebuilds indexes, lints, and optionally commits. Supports `--dry-run` and `--no-commit`.
- **`okf_update.py`** — page update helper: bumps `timestamp`, appends `log.md`, rebuilds indexes, lints, and optionally commits.
- **`okf_status.py`** — bundle health overview showing page counts by type, raw file count, and last log entry. Supports `--json` and `--tier all|global|local`.
- **`okf_diff.py`** — git diff for wiki pages, supporting `--previous N` and `--since <commit>` flags.
- **Tier support across all tooling** — `--tier all|global|local` flag on `okf_search.py`, `okf_lint.py`, `okf_status.py`, `okf_ingest.py`, `okf_update.py`, `okf_diff.py`. Resolves `~/.llm-wiki` (global) and `./.llm-wiki` (local) bundles. Added `resolve_bundles()` and `resolve_single_bundle()` to `okf_common.py`.
- **Contradiction detection in lint** — two new rules:
  - `duplicate-source-claim`: multiple factual pages citing the same `raw/<file>` with different titles.
  - `near-duplicate-title`: pages in the same subdirectory with identical or very similar titles but different sources.
- **`--strict-frontmatter` flag** on `okf_lint.py` — warns when the yamlish parser may have silently dropped content (empty lists that suggest unparseable nested YAML or multiline scalars).
- **`--from-readme` flag** on `okf_init.py` — infers wiki title and description from a `README.md` in the current working directory.
- **`bump_timestamp()` and `slugify()`** helpers added to `okf_common.py`.
- **`FACTUAL_TYPES` constant** exported from `okf_common.py`.
- **`_STOPWORDS` set** and `tokenize_query()`, `_term_hits()`, `search_bundle()` in `okf_common.py`.

### Changed
- **SKILL.md** rewritten to document all new operations (SEARCH, STATUS, INGEST, UPDATE, DIFF) and cross-platform script-path resolution.
- **`okf_spec.md`** expanded with a full "Frontmatter syntax (yamlish subset)" section documenting supported and unsupported YAML constructs.
- **`install.sh`** updated with new script names in Copilot/Windsurf sections.
- **`okf_lint.py`** now supports `--bundle`, `--tier`, and `bundle_dir` as optional positional arg.

### Fixed
- Cross-platform script-path inconsistency: SKILL.md now explicitly documents that scripts may be at `scripts/okf_*.py` (Pi/Claude) or on PATH (Cursor/Copilot/Windsurf).

## [1.1.0] - 2026-07-02

### Added
- Multi-platform installer (`install.sh`) for Claude Code, Cursor, Copilot, Windsurf, Pi.
- `.claude-plugin/plugin.json` for Claude marketplace.
- `okf_now.py` timestamp helper.

### Changed
- Leaner README.

## [1.0.0] - 2026-06-30

### Added
- Initial release: OKF-light skill package with `okf_init.py`, `okf_index.py`, `okf_lint.py`, `okf_common.py`.
- Query-first discipline enforced by SKILL.md.
- Two-tier architecture (`raw/` immutable, concept pages editable).
- Yamlish frontmatter parser, link normalizer, orphan detection, MISUSE field mapping.
- OKF v0.1 specification reference.
