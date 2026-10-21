import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mkdocs.exceptions import ConfigurationError
import yaml

from scripts import eii_publication as publication


class EIIPublicationTests(unittest.TestCase):
    def test_approval_requires_exact_repository_commit_and_allowlists(self):
        original = publication.manifest()
        for change in [{"commit": "main"}, {"repository": "https://example.org/source"}, {"documents": []}, {"references": []}]:
            with patch.object(Path, "read_text", return_value=json.dumps(original | change)):
                with self.assertRaises(ConfigurationError):
                    publication.manifest()

    def test_missing_or_modified_source_fails_closed(self):
        for code in [0, 128]:
            with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=b"changed")):
                with self.assertRaises(ConfigurationError):
                    publication.read_document("source", "a" * 40, {"source": "README.md", "sha256": "0" * 64})

    def test_linked_references_are_checked_but_not_imported(self):
        generated = {}
        def generate(config, page, **kw):
            generated[page] = kw["content"]
            return page
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(publication, "read_document", side_effect=lambda source, commit, item: item["source"]) as read, \
                patch.object(publication.File, "generated", side_effect=generate):
            publication.on_files([], SimpleNamespace())
        self.assertEqual(read.call_count, 4)
        self.assertEqual(set(generated), {publication.CATALOGUE, publication.GUIDE, publication.MACHINE})
        self.assertEqual(generated[publication.CATALOGUE], "EII_Scientific_Reference_Register.md")
        self.assertEqual(generated[publication.GUIDE], "README.md")
        commit = publication.manifest()["commit"]
        self.assertIn(f"/{commit}/EII_Machine_Reference.md", generated[publication.MACHINE])
        self.assertIn(f"https://raw.githubusercontent.com/ecological-interaction/EII/{commit}/", generated[publication.MACHINE])
        self.assertIn("do not grant reuse permission", generated[publication.MACHINE])

    def test_presentation_changes_only_links_and_navigation(self):
        page = lambda uri: SimpleNamespace(file=SimpleNamespace(src_uri=uri))
        table = "| EII ID | Variable | Kind | Main approaches | Use |\n|---|---|---|---|---|\n| VEG-001 | NDVI | D/P | GIS | Greenness. |\n"
        self.assertTrue(publication.on_page_markdown(table, page(publication.CATALOGUE)).endswith(table))
        guide = "[Science](EII_Scientific_Reference_Register.md) [Machine](EII_Machine_Reference.md) [Subset](EII%20-%20Remote%20Sensing.md) [Cite](CITATION.cff)"
        result = publication.on_page_markdown(guide, page(publication.GUIDE))
        self.assertIn("[Science](index.md)", result)
        self.assertIn("[Machine](machine-reference.md)", result)
        self.assertIn(f"/blob/{publication.manifest()['commit']}/EII%20-%20Remote%20Sensing.md", result)
        overview = "# Authoritative overview\n[GISDS](GISDS/index.md)"
        self.assertEqual(publication.on_page_markdown(overview, page("information/index.md")), overview + publication.OVERVIEW_NAV)
        self.assertEqual(publication.on_page_markdown(guide, page("information/GISDS/index.md")), guide)

    def test_hosted_build_needs_source_and_duplicate_destinations_fail(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([], SimpleNamespace())
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([SimpleNamespace(src_uri=publication.MACHINE)], SimpleNamespace())

    def test_workflow_preserves_deployment_and_public_fetch(self):
        workflow = yaml.load((publication.ROOT / ".github/workflows/deploy.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        steps = workflow["jobs"]["deploy"]["steps"]
        step = next(s for s in steps if s["name"] == "Retrieve approved EII commit anonymously")
        self.assertEqual(step["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(step["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertIn('"credential.helper="', step["run"])
        self.assertIn('"--depth=1"', step["run"])
        build = next(s for s in steps if s["name"] == "Build website")
        for key in ['EII_SOURCE', 'EIRKB_SOURCE', 'INFORMATION_SOURCE', 'GISDS_SOURCE']:
            self.assertIn(key, build['env'])
