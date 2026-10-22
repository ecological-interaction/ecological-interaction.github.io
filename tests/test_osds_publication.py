import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mkdocs.exceptions import ConfigurationError
import yaml

from scripts import osds_publication as publication


class OSDSPublicationTests(unittest.TestCase):
    def test_approval_requires_exact_repository_commit_and_allowlists(self):
        original = publication.manifest()
        for change in [{"commit": "main"}, {"repository": "https://example.org/source"}, {"documents": []}, {"references": []}, {"assets": []}, {"assets": [{"source": "render_osds_federation.py", "page": "arbitrary.svg", "sha256": "0" * 64}]}]:
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
                patch.object(publication.File, "generated", side_effect=generate), \
                patch.object(publication, "read_file", return_value=b"<svg/>") as read_asset:
            publication.on_files([], SimpleNamespace())
        self.assertEqual(read.call_count, 3)
        self.assertEqual(read_asset.call_count, 1)
        self.assertEqual(generated[next(iter(publication.ASSETS.values()))], b"<svg/>")
        self.assertEqual(set(generated), {publication.CATALOGUE, publication.GUIDE, publication.MACHINE, *publication.ASSETS.values()})
        self.assertEqual(generated[publication.CATALOGUE], "OSDS_Scientific_Reference_Register.md")
        self.assertEqual(generated[publication.GUIDE], "README.md")
        commit = publication.manifest()["commit"]
        self.assertIn(f"/{commit}/OSDS_Machine_Reference.md", generated[publication.MACHINE])
        self.assertIn(f"https://raw.githubusercontent.com/ecological-interaction/OSDS/{commit}/", generated[publication.MACHINE])
        self.assertIn("do not grant reuse permission", generated[publication.MACHINE])

    def test_presentation_changes_only_links_and_navigation(self):
        page = lambda uri: SimpleNamespace(file=SimpleNamespace(src_uri=uri))
        table = "| OSDS ID | Variable | Kind | Main approaches | Use |\n|---|---|---|---|---|\n| VEG-001 | NDVI | D/P | GIS | Greenness. |\n"
        self.assertTrue(publication.on_page_markdown(table, page(publication.CATALOGUE)).endswith(table))
        guide = "[Science](OSDS_Scientific_Reference_Register.md) [Machine](OSDS_Machine_Reference.md) [Cite](CITATION.cff)"
        result = publication.on_page_markdown(guide, page(publication.GUIDE))
        self.assertIn("[Science](index.md)", result)
        self.assertIn("[Machine](machine-reference.md)", result)
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
        step = next(s for s in steps if s["name"] == "Retrieve approved OSDS commit anonymously")
        self.assertEqual(step["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(step["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertIn('"credential.helper="', step["run"])
        self.assertIn('"--depth=1"', step["run"])
        build = next(s for s in steps if s["name"] == "Build website")
        for key in ['OSDS_SOURCE', 'EII_SOURCE', 'EIRKB_SOURCE', 'INFORMATION_SOURCE', 'GISDS_SOURCE']:
            self.assertIn(key, build['env'])


    def test_all_62_real_record_fragments_and_scientific_cells_are_preserved(self):
        import re
        data = publication.manifest()
        source = Path(os.environ.get("OSDS_SOURCE", str(publication.ROOT.parent / "ecological-information/OSDS"))).expanduser()
        science_item = next(d for d in data["documents"] if d["source"] == "OSDS_Scientific_Reference_Register.md")
        science = publication.read_document(source, data["commit"], science_item)
        machine = publication.read_document(source, data["commit"], data["references"][0])
        objects = [json.loads(block) for block in re.findall(r"```json\s*\n(.*?)\n```", machine, re.S)]
        self.assertEqual(len(objects), 63)
        ids = [record["id"] for record in objects[1:]]
        self.assertEqual(ids, [f"SRC-{n:03}" for n in range(1, 63)])
        anchors = re.findall(r'<a id="([^"]+)">', machine)
        rendered = publication.on_page_markdown(science, SimpleNamespace(file=SimpleNamespace(src_uri=publication.CATALOGUE)))
        base = publication.source_url(data, "OSDS_Machine_Reference.md")
        for identifier, anchor in zip(ids, anchors):
            self.assertEqual(identifier.lower(), anchor)
            self.assertIn(f"[{identifier}]({base}#{anchor})", rendered)
        self.assertNotIn("](" + "OSDS_Machine_Reference.md#", rendered)
        # Reversing only the approved link transformation recovers every table row verbatim.
        table_rows = lambda text: [line for line in text.splitlines() if line.startswith("|")]
        self.assertEqual(table_rows(rendered.replace(base + "#", "OSDS_Machine_Reference.md#")), table_rows(science))
        self.assertNotIn('"block_type": "source_record"', publication.machine_access(data))

    def test_fragment_and_guide_links_are_mapped_without_affecting_other_pages(self):
        page = SimpleNamespace(file=SimpleNamespace(src_uri=publication.GUIDE))
        original = "[Record](OSDS_Machine_Reference.md#src-062) [Machine](OSDS_Machine_Reference.md) [History](CHANGELOG.md)"
        result = publication.on_page_markdown(original, page)
        data = publication.manifest()
        self.assertIn(publication.source_url(data, "OSDS_Machine_Reference.md") + "#src-062", result)
        self.assertIn("[Machine](machine-reference.md)", result)
        self.assertIn(publication.source_url(data, "CHANGELOG.md"), result)
        unrelated = SimpleNamespace(file=SimpleNamespace(src_uri="information/EII/index.md"))
        self.assertEqual(publication.on_page_markdown(original, unrelated), original)


    def test_svg_is_read_verbatim_from_approved_commit(self):
        data = publication.manifest()
        source = Path(os.environ.get("OSDS_SOURCE", str(publication.ROOT.parent / "ecological-information/OSDS")))
        item = data["assets"][0]
        svg = publication.read_file(source, data["commit"], item)
        self.assertIsInstance(svg, bytes)
        self.assertIn(b'OSDS', svg)
        self.assertIn(b'Historical records', svg)
        self.assertIn(b'IRKB', svg)
        with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=svg)) as run:
            self.assertEqual(publication.read_file(source, data["commit"], item), svg)
        self.assertIn(f"{data['commit']}:{item['source']}", run.call_args.args[0])
        self.assertNotIn("render_osds_federation.py", run.call_args.args[0])

    def test_missing_or_checksum_mismatched_svg_stops_publication(self):
        data = publication.manifest()
        item = data["assets"][0]
        for code, content in [(128, b""), (0, b"<svg>modified</svg>")]:
            with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=content)):
                with self.assertRaises(ConfigurationError):
                    publication.read_file("source", data["commit"], item)
        with patch.dict(os.environ, {}, clear=True), \
                patch.object(publication, "read_document", return_value="# Source"), \
                patch.object(publication, "read_file", side_effect=ConfigurationError("SVG missing")), \
                patch.object(publication.File, "generated"):
            with self.assertRaises(ConfigurationError):
                publication.on_files([], SimpleNamespace())

    def test_asset_collision_is_rejected_and_guide_image_path_is_preserved(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_files([SimpleNamespace(src_uri=next(iter(publication.ASSETS.values())))], SimpleNamespace())
        source = "# Observational Systems and Data Sources (OSDS)\n\n![Federation](assets/diagrams/osds_federation.svg)\n"
        self.assertEqual(publication.on_page_markdown(source, SimpleNamespace(file=SimpleNamespace(src_uri=publication.GUIDE))), source)
