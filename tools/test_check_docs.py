"""Regression tests for the dependency-free documentation checker."""

import tempfile
import unittest
from pathlib import Path

from check_docs import anchors, check, prose


class DocumentationLinks(unittest.TestCase):
    def test_headings_and_duplicate_slugs(self):
        self.assertEqual(
            anchors("# Hello `API`\n## Hello API\n## Français\n"),
            {"hello-api", "hello-api-1", "français"},
        )

    def test_fenced_examples_are_not_links(self):
        self.assertEqual(
            prose("Before\n```md\n[Example](missing)\n```\nAfter"), "Before\nAfter"
        )

    def test_files_anchors_html_and_external_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text(
                '# Intro\n[Self](#intro)\n[Web](https://example.com)\n<img src="missing.png">\n[Bad](#absent)\n',
                encoding="utf-8",
            )
            failures = check(source, root)
            self.assertEqual(len(failures), 2)
            self.assertTrue(any("missing.png" in item for item in failures))
            self.assertTrue(any("#absent" in item for item in failures))

    def test_encoded_space_and_reference_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "My Guide.md").write_text("# Guide", encoding="utf-8")
            source = root / "README.md"
            source.write_text(
                "[Guide](<My Guide.md#guide>)\n[ref]: My%20Guide.md#guide\n",
                encoding="utf-8",
            )
            self.assertEqual(check(source, root), [])


if __name__ == "__main__":
    unittest.main()
