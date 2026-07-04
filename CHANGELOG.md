# Changelog

## [1.2.0] - 2026-07-03

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
