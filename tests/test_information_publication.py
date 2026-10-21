import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mkdocs.exceptions import ConfigurationError
import yaml

from scripts import information_publication as publication


class InformationPublicationTests(unittest.TestCase):
    def test_manifest_rejects_moving_refs_and_unapproved_files(self):
        original = publication.manifest()
        for change in [{"commit": "main"}, {"repository": "https://example.org/source"}, {"files": []}]:
            with patch.object(Path, "read_text", return_value=__import__("json").dumps(original | change)):
                with self.assertRaises(ConfigurationError):
                    publication.manifest()

    def test_checksum_failure_stops_import(self):
        item = {"source": "README.md", "sha256": "0" * 64}
        with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=b"changed")):
            with self.assertRaises(ConfigurationError):
                publication.read_file("source", "a" * 40, item)

    def test_import_maps_only_links_and_preserves_binary(self):
        content = {
            "README.md": b"# Research\n[DRM](DRM/README.md)\n![Diagram](assets/diagrams/federated-knowledge-systems.png)",
            "DRM/README.md": b"[Overview](../README.md)",
            "assets/diagrams/federated-knowledge-systems.png": b"\x89PNG\r\n\x1a\n\xff",
            "REORGANISATION.json": b'{"history": true}',
        }
        generated = {}
        def generate(config, page, **kw):
            generated[page] = kw["content"]
            return page
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(publication, "read_file", side_effect=lambda source, commit, item: content[item["source"]]), \
                patch.object(publication.File, "generated", side_effect=generate):
            publication.on_files([], SimpleNamespace())
        self.assertEqual(set(generated), set(publication.EXPECTED.values()))
        self.assertEqual(generated["information/index.md"], content["README.md"].decode().replace("DRM/README.md", "DRM/index.md"))
        self.assertEqual(generated["information/DRM/index.md"], "[Overview](../index.md)")
        for name in ["REORGANISATION.json", "assets/diagrams/federated-knowledge-systems.png"]:
            self.assertEqual(generated[publication.EXPECTED[name]], content[name])

    def test_hosted_build_requires_source_and_rejects_collisions(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([], SimpleNamespace())
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([SimpleNamespace(src_uri="information/index.md")], SimpleNamespace())

    def test_workflow_keeps_eirkb_and_anonymous_information_fetch(self):
        workflow = yaml.load((publication.ROOT / ".github/workflows/deploy.yml").read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        steps = workflow["jobs"]["deploy"]["steps"]
        fetch = next(s for s in steps if s["name"] == "Retrieve approved Information commit anonymously")
        self.assertEqual(fetch["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(fetch["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertIn('"credential.helper="', fetch["run"])
        build = next(s for s in steps if s["name"] == "Build website")
        self.assertIn("EIRKB_SOURCE", build["env"])
        self.assertIn("INFORMATION_SOURCE", build["env"])
        self.assertNotIn("secrets.", fetch["run"])
