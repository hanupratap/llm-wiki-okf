"""Tests for okf_index.py — marker pair insertion, index regeneration."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "llm-wiki-okf" / "scripts"))

from okf_common import MARKER, MARKER_CLOSE
from okf_index import main as index_main


class TestIndexRegeneration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        (self.root / "notes").mkdir(parents=True)
        (self.root / "sources").mkdir(parents=True)
        (self.root / "raw").mkdir()
        (self.root / "log.md").write_text("# Log\n")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _run_index(self):
        import sys as _sys
        old_argv = _sys.argv
        try:
            _sys.argv = ["okf_index.py", str(self.root)]
            return index_main()
        finally:
            _sys.argv = old_argv

    def test_creates_index_with_marker_pair(self):
        # Add a concept page
        (self.root / "notes" / "arch.md").write_text(
            "---\ntype: Note\ntitle: Architecture\ntimestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
        )

        self._run_index()

        idx = self.root / "notes" / "index.md"
        self.assertTrue(idx.exists())
        content = idx.read_text()
        self.assertIn(MARKER, content)
        self.assertIn(MARKER_CLOSE, content)
        self.assertIn("Architecture", content)

    def test_legacy_single_marker_migrated(self):
        # Existing index with old single-marker format
        (self.root / "notes" / "index.md").write_text(
            "---\ntype: Index\ntitle: Notes\ntimestamp: 2026-07-03T00:00:00Z\n---\n\n"
            "# Notes\n\n"
            f"{MARKER}\n"
            "- [Architecture](/notes/arch.md)\n"
        )
        (self.root / "notes" / "arch.md").write_text(
            "---\ntype: Note\ntitle: Architecture\ntimestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
        )

        self._run_index()

        idx = self.root / "notes" / "index.md"
        content = idx.read_text()
        self.assertIn(MARKER, content)
        self.assertIn(MARKER_CLOSE, content)
        self.assertIn("Architecture", content)

    def test_idempotent(self):
        (self.root / "notes" / "arch.md").write_text(
            "---\ntype: Note\ntitle: Architecture\ntimestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
        )

        self._run_index()
        idx = self.root / "notes" / "index.md"
        first = idx.read_text()

        self._run_index()
        second = idx.read_text()

        self.assertEqual(first, second)

    def test_dry_run(self):
        (self.root / "notes" / "arch.md").write_text(
            "---\ntype: Note\ntitle: Architecture\ntimestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
        )

        import sys as _sys
        old_argv = _sys.argv
        try:
            _sys.argv = ["okf_index.py", str(self.root), "--dry-run"]
            rc = index_main()
            self.assertEqual(rc, 0)
        finally:
            _sys.argv = old_argv

        # File should not be created in dry-run
        self.assertFalse((self.root / "notes" / "index.md").exists())

    def test_reserved_files_excluded(self):
        (self.root / "notes" / "arch.md").write_text(
            "---\ntype: Note\ntitle: Architecture\ntimestamp: 2026-07-03T00:00:00Z\n---\n\nBody.\n"
        )
        # index.md and log.md exist at root but should not appear
        (self.root / "index.md").write_text("# Wiki\n")

        self._run_index()

        idx = self.root / "notes" / "index.md"
        content = idx.read_text()
        # index.md and log.md should not be listed
        self.assertNotIn("index.md", content.split(MARKER)[1] if MARKER in content else content)
        self.assertNotIn("log.md", content.split(MARKER)[1] if MARKER in content else content)


if __name__ == "__main__":
    unittest.main()
