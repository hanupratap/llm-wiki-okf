"""Tests for okf_lint.py — contradiction detection, orphan checks, strict-frontmatter."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "llm-wiki-okf" / "scripts"))

from okf_lint import _lint_bundle as lint_bundle


class _Args:
    """Minimal argparse.Namespace substitute for lint options."""
    def __init__(self, **kwargs):
        self.stale_days = kwargs.get("stale_days", 90)
        self.strict_frontmatter = kwargs.get("strict_frontmatter", False)


class BaseBundleTest(unittest.TestCase):
    """Base test with a helper to create and manage temporary bundles."""

    def _make_bundle(self, pages: dict[str, str]) -> Path:
        """Create a temporary bundle from {rel_path: content} dict.

        Returns the bundle root. The temporary directory is cleaned up
        automatically after the test.
        """
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        for rel, content in pages.items():
            full = root / rel.lstrip("/")
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content)

        return root


class TestOrphanDetection(BaseBundleTest):
    def test_linked_page_not_orphan(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/arch.md": (
                "---\ntype: Note\ntitle: Architecture\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\n"
                "See [User Service](/entities/user.md).\n"
            ),
            "entities/user.md": (
                "---\ntype: Note\ntitle: User Service\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nDetails.\n"
            ),
        })
        errors, warnings, count = lint_bundle(root, _Args())
        self.assertGreater(count, 0)
        orphan_files = [w["file"] for w in warnings if w["rule"] == "orphan"]
        self.assertNotIn("/entities/user.md", orphan_files)

    def test_unlinked_page_is_orphan(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/arch.md": (
                "---\ntype: Note\ntitle: Architecture\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nJust some notes.\n"
            ),
        })
        _, warnings, _ = lint_bundle(root, _Args())
        orphan_files = [w["file"] for w in warnings if w["rule"] == "orphan"]
        self.assertIn("/notes/arch.md", orphan_files)


class TestBrokenLinks(BaseBundleTest):
    def test_valid_link_ok(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/a.md": (
                "---\ntype: Note\ntitle: A\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\n[Link](/notes/b.md)\n"
            ),
            "notes/b.md": (
                "---\ntype: Note\ntitle: B\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nContent.\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        broken = [e for e in errors if e["rule"] == "broken-link"]
        self.assertEqual(len(broken), 0)

    def test_broken_link_flagged(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/a.md": (
                "---\ntype: Note\ntitle: A\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\n[Link](/notes/missing.md)\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        broken = [e for e in errors if e["rule"] == "broken-link"]
        self.assertEqual(len(broken), 1)


class TestDuplicateSourceClaim(BaseBundleTest):
    def test_duplicate_source_different_title(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "raw/design.md": "# Design\n",
            "sources/page1.md": (
                "---\ntype: Source\ntitle: Design Doc\n"
                "sources: [raw/design.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nSummary.\n"
            ),
            "sources/page2.md": (
                "---\ntype: Source\ntitle: Architecture Doc\n"
                "sources: [raw/design.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nAnother summary.\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        dup = [e for e in errors if e["rule"] == "duplicate-source-claim"]
        self.assertEqual(len(dup), 1)

    def test_same_source_same_title_no_error(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "raw/design.md": "# Design\n",
            "sources/page1.md": (
                "---\ntype: Source\ntitle: Design Doc\n"
                "sources: [raw/design.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nSummary.\n"
            ),
            "sources/page2.md": (
                "---\ntype: Source\ntitle: Design Doc\n"
                "sources: [raw/design.md]\n"
                "timestamp: 2026-07-04T00:00:00Z\n---\n\nUpdate.\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        dup = [e for e in errors if e["rule"] == "duplicate-source-claim"]
        self.assertEqual(len(dup), 0)


class TestNearDuplicateTitle(BaseBundleTest):
    def test_duplicate_title_warns(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "entities/user1.md": (
                "---\ntype: Note\ntitle: User\n"
                "sources: [raw/a.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nUser details.\n"
            ),
            "entities/user2.md": (
                "---\ntype: Note\ntitle: User\n"
                "sources: [raw/b.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nOther user details.\n"
            ),
        })
        _, warnings, _ = lint_bundle(root, _Args())
        dup = [w for w in warnings if w["rule"] == "near-duplicate-title"]
        self.assertEqual(len(dup), 1)

    def test_unique_titles_no_warn(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "entities/user.md": (
                "---\ntype: Note\ntitle: User Service\n"
                "sources: [raw/a.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\n.\n"
            ),
            "entities/order.md": (
                "---\ntype: Note\ntitle: Order Service\n"
                "sources: [raw/b.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\n.\n"
            ),
        })
        _, warnings, _ = lint_bundle(root, _Args())
        dup = [w for w in warnings if w["rule"] == "near-duplicate-title"]
        self.assertEqual(len(dup), 0)


class TestStrictFrontmatter(BaseBundleTest):
    def test_empty_list_warns(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/test.md": (
                "---\ntype: Note\ntitle: Test\n"
                "foo:\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
            ),
        })
        _, warnings, _ = lint_bundle(root, _Args(strict_frontmatter=True))
        empty_list = [w for w in warnings if w["rule"] == "suspicious-empty-list"]
        self.assertEqual(len(empty_list), 1)
        self.assertIn("foo", empty_list[0]["message"])

    def test_no_warn_without_strict(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/test.md": (
                "---\ntype: Note\ntitle: Test\n"
                "foo:\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
            ),
        })
        _, warnings, _ = lint_bundle(root, _Args(strict_frontmatter=False))
        empty_list = [w for w in warnings if w["rule"] == "suspicious-empty-list"]
        self.assertEqual(len(empty_list), 0)


class TestMissingType(BaseBundleTest):
    def test_missing_type_flagged(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/test.md": (
                "---\ntitle: Test\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        missing = [e for e in errors if e["rule"] == "missing-type"]
        self.assertEqual(len(missing), 1)


class TestMisuseFields(BaseBundleTest):
    def test_name_misuse_flagged(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "notes/test.md": (
                "---\ntype: Note\nname: WrongName\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        misuse = [e for e in errors if e["rule"] == "reserved-field-misuse"]
        self.assertEqual(len(misuse), 1)
        self.assertIn("name", misuse[0]["message"])


class TestUnresolvableSource(BaseBundleTest):
    def test_missing_raw_file_flagged(self):
        root = self._make_bundle({
            "index.md": "# Wiki\n",
            "log.md": "# Log\n",
            "sources/summary.md": (
                "---\ntype: Source\ntitle: Summary\n"
                "sources: [raw/nonexistent.md]\n"
                "timestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
            ),
        })
        errors, _, _ = lint_bundle(root, _Args())
        unres = [e for e in errors if e["rule"] == "unresolvable-source"]
        self.assertEqual(len(unres), 1)


if __name__ == "__main__":
    unittest.main()
