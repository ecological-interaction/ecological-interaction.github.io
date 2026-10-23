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
            "ARCHITECTURE.md": b"[Overview](README.md) [History](REORGANISATION.json)",
            "assets/diagrams/federated_knowledge_systems.svg": b'<svg xmlns="http://www.w3.org/2000/svg"/>',
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
        self.assertEqual(generated["information/architecture.md"], "[Overview](index.md) [History](REORGANISATION.json)")
        for name in ["REORGANISATION.json", "assets/diagrams/federated-knowledge-systems.png", "assets/diagrams/federated_knowledge_systems.svg"]:
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


    def test_missing_or_mismatched_svg_fails_closed(self):
        item = next(i for i in publication.manifest()["files"] if i["source"].endswith(".svg"))
        for code, data in [(128, b""), (0, b"<svg>modified</svg>")]:
            with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=data)):
                with self.assertRaises(ConfigurationError):
                    publication.read_file("source", "a" * 40, item)

    def test_approved_pin_real_checksums_and_generated_content(self):
        import re
        import markdown
        data = publication.manifest()
        self.assertEqual(data["commit"], "78795d7ac4de670ff56921b8aa4638cab4a40eec")
        source = Path(os.environ.get("INFORMATION_SOURCE", str(publication.ROOT.parent / "ecological-information/ecological-information")))
        original = {item["source"]: publication.read_file(source, data["commit"], item) for item in data["files"]}
        generated = {}
        def generate(config, page, **kw):
            generated[page] = kw["content"]
            return page
        with patch.dict(os.environ, {"INFORMATION_SOURCE": str(source)}), \
                patch.object(publication.File, "generated", side_effect=generate):
            publication.on_files([], SimpleNamespace())
        overview = generated["information/index.md"]
        self.assertTrue(overview.splitlines()[2].startswith("!["))
        self.assertIn("](architecture.md)", overview)
        self.assertIn("](DRM/index.md)", overview)
        self.assertEqual(len(re.findall(r"^\| \*\*", overview, re.M)), 9)
        self.assertIn("[the Overview](index.md)", generated["information/architecture.md"])
        for name in ["assets/diagrams/federated_knowledge_systems.svg", "assets/diagrams/federated-knowledge-systems.png", "REORGANISATION.json"]:
            self.assertEqual(generated[publication.EXPECTED[name]], original[name])
        svg = original["assets/diagrams/federated_knowledge_systems.svg"].decode().lower()
        for colour in ["#cce3f9", "#e1daf0", "#e1f0e6", "#feeec9", "#eaedf1"]:
            self.assertIn(colour, svg)
        rendered = markdown.markdown(overview, extensions=["tables", "fenced_code"])
        self.assertLess(rendered.index("<h1>"), rendered.index("<img"))
        self.assertLess(rendered.index("<img"), rendered.index("<h2>Introduction"))

    def test_overview_consolidation_keeps_directory_and_other_pages(self):
        from scripts import gisds_publication, eii_publication, osds_publication
        page = SimpleNamespace(file=SimpleNamespace(src_uri="information/index.md"))
        original = "# Overview\n" + "\n".join(f"[Read {name}](https://ecological-interaction.github.io/information/{name}/)" for name in ["GISDS", "EII", "OSDS"])
        appended = original
        for hook in [gisds_publication, eii_publication, osds_publication]:
            appended = hook.on_page_markdown(appended, page)
        self.assertEqual(publication.on_page_markdown(appended, page), original)
        self.assertEqual(publication.on_page_markdown("# Legacy" + osds_publication.OVERVIEW_NAV, page), "# Legacy" + osds_publication.OVERVIEW_NAV)
        page.file.src_uri = "information/OSDS/index.md"
        self.assertEqual(publication.on_page_markdown(appended, page), appended)
        self.assertEqual(publication.on_page_markdown.mkdocs_priority, -100)

    def test_architecture_navigation_and_hosted_validation_source(self):
        config = yaml.safe_load((publication.ROOT / "mkdocs.yml").read_text())
        information = next(item["Information"] for item in config["nav"] if "Information" in item)
        self.assertIn({"Architecture and history": "information/architecture.md"}, information)
        workflow = yaml.load((publication.ROOT / ".github/workflows/deploy.yml").read_text(), Loader=yaml.BaseLoader)
        tests = next(s for s in workflow["jobs"]["deploy"]["steps"] if s["name"] == "Test publication import")
        self.assertIn("INFORMATION_SOURCE", tests["env"])
