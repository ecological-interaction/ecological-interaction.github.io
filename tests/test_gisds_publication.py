import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mkdocs.exceptions import ConfigurationError
import yaml

from scripts import gisds_publication as publication


class GISDSPublicationTests(unittest.TestCase):
    def test_only_approved_repository_commit_and_documents(self):
        original = publication.manifest()
        for change in [{"commit": "main"}, {"repository": "https://example.org/source"}, {"documents": []}]:
            with patch.object(Path, "read_text", return_value=json.dumps(original | change)):
                with self.assertRaises(ConfigurationError):
                    publication.manifest()

    def test_unavailable_or_changed_source_fails(self):
        item = {"source": "GISDS.md", "sha256": "0" * 64}
        for code in [0, 128]:
            with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=b"changed")):
                with self.assertRaises(ConfigurationError):
                    publication.read_document("source", "a" * 40, item)

    def test_import_is_verbatim_and_preserves_other_destinations(self):
        existing = SimpleNamespace(src_uri="information/index.md")
        generated = {}
        def generate(config, page, **kw):
            generated[page] = kw["content"]
            return page
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(publication, "read_document", side_effect=lambda source, commit, item: item["source"]), \
                patch.object(publication.File, "generated", side_effect=generate):
            files = publication.on_files([existing], SimpleNamespace())
        self.assertIs(files[0], existing)
        self.assertEqual(generated, {publication.CATALOGUE: "GISDS.md", publication.GUIDE: "README.md"})

    def test_presentation_changes_only_framing_and_local_links(self):
        page = lambda uri: SimpleNamespace(file=SimpleNamespace(src_uri=uri))
        table = "| ID | Resource |\n|---|---|\n| RS001 | Source |\n"
        self.assertTrue(publication.on_page_markdown(table, page(publication.CATALOGUE)).endswith(table))
        guide = "# Research\n[Catalogue](GISDS.md)\n[Citation](CITATION.cff)\n[History](CHANGELOG.md)"
        rendered = publication.on_page_markdown(guide, page(publication.GUIDE))
        self.assertIn("[Catalogue](index.md)", rendered)
        commit = publication.manifest()["commit"]
        for name in ["CITATION.cff", "CHANGELOG.md"]:
            self.assertIn(f"/blob/{commit}/{name}", rendered)
        overview = "# Original umbrella\n"
        self.assertEqual(publication.on_page_markdown(overview, page("information/index.md")), overview + publication.OVERVIEW_NAV)
        self.assertEqual(publication.on_page_markdown(guide, page("information/EIRKB/index.md")), guide)

    def test_workflow_and_hosted_build_require_public_source(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([], SimpleNamespace())
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([SimpleNamespace(src_uri=publication.CATALOGUE)], SimpleNamespace())
        workflow = yaml.load((publication.ROOT / ".github/workflows/deploy.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        steps = workflow["jobs"]["deploy"]["steps"]
        step = next(s for s in steps if s["name"] == "Retrieve approved GISDS commit anonymously")
        self.assertEqual(step["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(step["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertIn('"credential.helper="', step["run"])
        self.assertIn('"--depth=1"', step["run"])
        self.assertNotIn("secrets.", step["run"])
        build = next(s for s in steps if s["name"] == "Build website")
        self.assertIn("GISDS_SOURCE", build["env"])
        self.assertIn("EIRKB_SOURCE", build["env"])
        self.assertIn("INFORMATION_SOURCE", build["env"])
