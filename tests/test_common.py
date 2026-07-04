"""Tests for okf_common.py — parser, link normalizer, search, tiers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# Ensure scripts dir is on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "llm-wiki-okf" / "scripts"))

from okf_common import (
    FACTUAL_TYPES,
    _parse_yamlish,
    _rel_target,
    _term_hits,
    bump_timestamp,
    load_bundle,
    now_iso,
    parse_frontmatter,
    resolve_bundles,
    resolve_single_bundle,
    search_bundle,
    slugify,
    tokenize_query,
    valid_iso8601,
)


class TestParseYamlish(unittest.TestCase):
    def test_scalar(self):
        fm = _parse_yamlish("type: Note\ntitle: Hello")
        self.assertEqual(fm["type"], "Note")
        self.assertEqual(fm["title"], "Hello")

    def test_inline_list(self):
        fm = _parse_yamlish("tags: [a, b, c]")
        self.assertEqual(fm["tags"], ["a", "b", "c"])

    def test_empty_inline_list(self):
        fm = _parse_yamlish("tags: []")
        self.assertEqual(fm["tags"], [])

    def test_block_list(self):
        fm = _parse_yamlish("sources:\n  - raw/foo.md\n  - raw/bar.md")
        self.assertEqual(fm["sources"], ["raw/foo.md", "raw/bar.md"])

    def test_block_list_empty(self):
        fm = _parse_yamlish("sources:\n")
        self.assertEqual(fm["sources"], [])

    def test_quoted_value(self):
        fm = _parse_yamlish('title: "Hello World"')
        self.assertEqual(fm["title"], "Hello World")

    def test_comment_line_skipped(self):
        fm = _parse_yamlish("type: Note\n# comment\ntitle: Hello")
        self.assertNotIn("#", fm)
        self.assertEqual(fm["title"], "Hello")

    def test_empty_input(self):
        fm = _parse_yamlish("")
        self.assertEqual(fm, {})


class TestParseFrontmatter(unittest.TestCase):
    def test_full(self):
        text = "---\ntype: Note\ntitle: Test\n---\n\nBody here."
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm["type"], "Note")
        self.assertEqual(body.strip(), "Body here.")

    def test_no_frontmatter(self):
        text = "# Just a heading\n\nBody."
        fm, body = parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, text)


class TestRelTarget(unittest.TestCase):
    def test_root_relative_passthrough(self):
        self.assertEqual(_rel_target("/notes/arch.md", "/entities/user.md"), "/notes/arch.md")

    def test_relative_in_same_dir(self):
        self.assertEqual(_rel_target("user.md", "/entities/index.md"), "/entities/user.md")

    def test_parent_traversal(self):
        self.assertEqual(
            _rel_target("../notes/arch.md", "/entities/sub/page.md"),
            "/entities/notes/arch.md",
        )

    def test_dot_current_dir(self):
        self.assertEqual(_rel_target("./user.md", "/entities/index.md"), "/entities/user.md")

    def test_external_url_passthrough(self):
        url = "https://example.com/doc.md"
        self.assertEqual(_rel_target(url, "/foo/bar.md"), url)

    def test_clean_dotdot(self):
        self.assertEqual(
            _rel_target("../../foo.md", "/a/b/c/page.md"),
            "/a/foo.md",
        )


class TestTokenizeQuery(unittest.TestCase):
    def test_simple(self):
        toks = tokenize_query("user service database")
        self.assertEqual(toks, ["user", "service", "database"])

    def test_stopwords_removed(self):
        toks = tokenize_query("the user and the service")
        self.assertEqual(toks, ["user", "service"])

    def test_short_tokens_removed(self):
        toks = tokenize_query("a b c database")
        self.assertEqual(toks, ["database"])

    def test_punctuation_stripped(self):
        toks = tokenize_query("user; service: database.")
        self.assertEqual(toks, ["user", "service", "database"])

    def test_kebab_case_split(self):
        toks = tokenize_query("user-service")
        self.assertEqual(toks, ["user", "service"])

    def test_cjk(self):
        toks = tokenize_query("用户 服务")
        self.assertGreater(len(toks), 0)


class TestTermHits(unittest.TestCase):
    def test_all_hit(self):
        self.assertEqual(_term_hits("the user service uses postgres", ["user", "service", "postgres"]), 3)

    def test_partial_hit(self):
        self.assertEqual(_term_hits("the user service", ["user", "postgres"]), 1)

    def test_no_hit(self):
        self.assertEqual(_term_hits("nothing here", ["user", "postgres"]), 0)

    def test_case_insensitive(self):
        self.assertEqual(_term_hits("USER Service", ["user", "service"]), 2)

    def test_empty_text(self):
        self.assertEqual(_term_hits("", ["user"]), 0)


class TestValidIso8601(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(valid_iso8601("2026-07-03T14:30:00Z"))

    def test_valid_no_z(self):
        self.assertTrue(valid_iso8601("2026-07-03T14:30:00"))

    def test_invalid(self):
        self.assertFalse(valid_iso8601("yesterday"))

    def test_datetime_object(self):
        from datetime import datetime, timezone
        self.assertTrue(valid_iso8601(datetime.now(timezone.utc)))


class TestNowIso(unittest.TestCase):
    def test_format(self):
        ts = now_iso()
        self.assertIn("T", ts)
        self.assertTrue(ts.endswith("Z"))
        self.assertTrue(valid_iso8601(ts))


class TestSlugify(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_special_chars(self):
        self.assertEqual(slugify("User's Guide!"), "users-guide")

    def test_short(self):
        self.assertEqual(slugify("a"), "a")

    def test_long_truncated(self):
        s = "x" * 100
        self.assertLessEqual(len(slugify(s)), 80)

    def test_empty(self):
        self.assertEqual(slugify(""), "untitled")


class TestBumpTimestamp(unittest.TestCase):
    def test_bumps(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntype: Note\ntitle: Test\ntimestamp: 2020-01-01T00:00:00Z\n---\n\nBody.")
            f.flush()
            path = Path(f.name)

        try:
            bump_timestamp(path)
            text = path.read_text()
            fm, _ = parse_frontmatter(text)
            self.assertNotEqual(fm["timestamp"], "2020-01-01T00:00:00Z")
            self.assertTrue(valid_iso8601(fm["timestamp"]))
        finally:
            path.unlink()

    def test_can_rebump(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntype: Note\ntitle: Test\ntimestamp: 2020-01-01T00:00:00Z\n---\n\nBody.")
            f.flush()
            path = Path(f.name)

        try:
            import time
            bump_timestamp(path)
            ts1 = parse_frontmatter(path.read_text())[0]["timestamp"]
            time.sleep(1.01)
            bump_timestamp(path)
            ts2 = parse_frontmatter(path.read_text())[0]["timestamp"]
            self.assertNotEqual(ts1, ts2)
        finally:
            path.unlink()


class TestSearchBundle(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)

        (root / "raw").mkdir()
        (root / "notes").mkdir()
        (root / "entities").mkdir()
        (root / "concepts").mkdir()

        # Make it look like an init'd bundle — index.md prevents search from choking
        (root / "index.md").write_text("# Wiki\n")
        (root / "log.md").write_text("# Log\n")

        # User service note
        (root / "notes" / "user-service.md").write_text(
            "---\ntype: Note\ntitle: User Service\ndescription: Handles user auth and profiles\n"
            "tags: [backend, auth]\ntimestamp: 2026-07-03T00:00:00Z\n---\n\n"
            "The user service connects to PostgreSQL.\n"
        )
        # Architecture note
        (root / "notes" / "architecture.md").write_text(
            "---\ntype: Note\ntitle: Architecture\ntags: [architecture]\n"
            "timestamp: 2026-07-01T00:00:00Z\n---\n\n"
            "We use microservices with gRPC for inter-service communication.\n"
        )
        # Entity page
        (root / "entities" / "postgres.md").write_text(
            "---\ntype: Note\ntitle: PostgreSQL\ndescription: Primary database\n"
            "tags: [database, infrastructure]\ntimestamp: 2026-07-02T00:00:00Z\n---\n\n"
            "PostgreSQL 16, hosted on RDS.\n"
        )
        self.root = root

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_exact_title_match(self):
        results = search_bundle(self.root, "user service")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["title"], "User Service")

    def test_description_match(self):
        results = search_bundle(self.root, "primary database")
        self.assertGreater(len(results), 0)
        titles = [r["title"] for r in results]
        self.assertIn("PostgreSQL", titles)

    def test_body_match(self):
        results = search_bundle(self.root, "microservices grpc")
        self.assertGreater(len(results), 0)
        titles = [r["title"] for r in results]
        self.assertIn("Architecture", titles)

    def test_tag_match(self):
        results = search_bundle(self.root, "auth")
        self.assertGreater(len(results), 0)
        titles = [r["title"] for r in results]
        self.assertIn("User Service", titles)

    def test_no_match(self):
        results = search_bundle(self.root, "zzzzzzzzz")
        self.assertEqual(len(results), 0)

    def test_max_results(self):
        results = search_bundle(self.root, "service", max_results=1)
        self.assertEqual(len(results), 1)

    def test_result_structure(self):
        results = search_bundle(self.root, "user")
        r = results[0]
        self.assertIn("title", r)
        self.assertIn("type", r)
        self.assertIn("score", r)
        self.assertIn("rel", r)
        self.assertIn("path", r)
        self.assertIn("preview", r)
        self.assertGreater(r["score"], 0)


class TestTierResolution(unittest.TestCase):
    def test_resolve_single_bundle_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / ".llm-wiki"
            root.mkdir()
            label, path = resolve_single_bundle(str(root))
            self.assertEqual(path, root.resolve())

    def test_resolve_single_bundle_nonexistent(self):
        result = resolve_single_bundle("/tmp/__nonexistent_llm_wiki__")
        self.assertIsNone(result)

    def test_resolve_bundles_returns_list(self):
        # At least returns a list (may be empty if bundles don't exist)
        bundles = resolve_bundles("local")
        self.assertIsInstance(bundles, list)


class TestFactualTypes(unittest.TestCase):
    def test_contains_source_and_note(self):
        self.assertIn("Source", FACTUAL_TYPES)
        self.assertIn("Note", FACTUAL_TYPES)


if __name__ == "__main__":
    unittest.main()
