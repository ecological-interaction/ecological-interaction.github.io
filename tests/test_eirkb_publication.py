import json
import tempfile
import re
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mkdocs.exceptions import ConfigurationError
import yaml

from scripts import eirkb_publication as publication


class EIRKBPublicationTests(unittest.TestCase):
    def config(self):
        return SimpleNamespace(
            nav=[{"Information": [
                {"Overview": "information/index.md"},
                {"EIRKB": [{"Introduction": publication.INTRODUCTION}]},
            ]}],
            site_dir="site",
        )

    def test_normal_build_imports_only_the_approved_pages(self):
        with patch.dict(os.environ, {}, clear=True):
            config = publication.on_config(self.config())
            def read_bytes(source, commit, item):
                return b"{}" if item["source"].endswith(".json") else b"<svg/>"
            with patch.object(publication, "read_document", return_value="# Research\n") as read, \
                    patch.object(publication, "read_file", side_effect=read_bytes), \
                    patch.object(publication.File, "generated", side_effect=lambda cfg, uri, **kw: uri):
                files = []
                self.assertIs(publication.on_files(files, config), files)
                self.assertEqual(read.call_count, len(publication.EXPECTED))
            self.assertEqual(set(files), {*publication.EXPECTED.values(), *publication.ASSETS.values(), publication.LEGACY_REGISTER, publication.MACHINE})
            self.assertEqual(config.site_dir, "site")
            page = SimpleNamespace(file=SimpleNamespace(src_uri="information/index.md"))
            self.assertIn("EIRKB/index.md", publication.on_page_markdown(publication.MARKER, page))

    def test_github_actions_cannot_enable_the_local_preview(self):
        with patch.dict(os.environ, {"EIRKB_PREVIEW": "1", "GITHUB_ACTIONS": "true"}):
            with self.assertRaises(ConfigurationError):
                publication.on_config(self.config())

    def test_normal_hosted_build_requires_an_explicit_source_checkout(self):
        with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=True):
            with self.assertRaises(ConfigurationError):
                publication.on_config(self.config())
        with patch.dict(os.environ, {
            "GITHUB_ACTIONS": "true", "EIRKB_SOURCE": "/runner/.sources/EIRKB"
        }, clear=True):
            config = publication.on_config(self.config())
            self.assertEqual(config.site_dir, "site")
            self.assertIn("EIRKB", config.nav[0]["Information"][1])

    def test_preview_output_is_separate_from_deployable_output(self):
        with patch.dict(os.environ, {"EIRKB_PREVIEW": "1", "GITHUB_ACTIONS": "false"}):
            config = publication.on_config(self.config())
            self.assertEqual(Path(config.site_dir), publication.ROOT / "site-preview")

    def test_document_is_read_from_explicit_commit_with_checksum(self):
        content = b"# Approved research\n"
        document = {
            "source": "research.md",
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        commit = "a" * 40
        with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(
            returncode=0, stdout=content
        )) as run:
            self.assertEqual(publication.read_document("source", commit, document), content.decode())
            self.assertEqual(run.call_args.args[0][-1], f"{commit}:research.md")
            document["sha256"] = "0" * 64
            with self.assertRaises(ConfigurationError):
                publication.read_document("source", commit, document)

    def test_moving_ref_or_missing_commit_fails_closed(self):
        document = {"source": "research.md", "sha256": "0" * 64}
        with self.assertRaises(ConfigurationError):
            publication.read_document("source", "main", document)
        with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(
            returncode=128, stdout=b""
        )):
            with self.assertRaises(ConfigurationError):
                publication.read_document("source", "a" * 40, document)

    def test_workbook_link_resolves_without_importing_the_source_asset(self):
        with patch.dict(os.environ, {"EIRKB_PREVIEW": "1", "GITHUB_ACTIONS": "false"}):
            publication.on_config(self.config())
            page = SimpleNamespace(file=SimpleNamespace(src_uri=publication.REGISTER))
            text = f"[Source workbook]({publication.WORKBOOK})"
            result = publication.on_page_markdown(text, page)
            self.assertIn(f"/blob/{publication.manifest()['commit']}/", result)
            self.assertIn("/_legacy%20registers/ecological_information_complete_reference_register_v0.1.xlsx)", result)

    def test_unapproved_document_mapping_fails_before_reading_source(self):
        with patch.dict(os.environ, {}, clear=True):
            config = publication.on_config(self.config())
            invalid = {"commit": "a" * 40, "documents": [{
                "source": "private-notes.md", "page": "notes.md", "sha256": "0" * 64,
            }]}
            with patch.object(publication, "_manifest", invalid), \
                    patch.object(publication, "read_document") as read:
                with self.assertRaises(ConfigurationError):
                    publication.on_files([], config)
                read.assert_not_called()

    def test_workflow_keeps_automatic_deployment_with_no_custom_source_secret(self):
        # BaseLoader preserves the YAML 'on' key rather than interpreting it as a bool.
        workflow = yaml.load(
            (publication.ROOT / ".github/workflows/deploy.yml").read_text(),
            Loader=yaml.BaseLoader,
        )
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        steps = workflow["jobs"]["deploy"]["steps"]
        source = next(s for s in steps if s["name"] == "Retrieve approved EIRKB commit anonymously")
        self.assertNotIn("uses", source)
        self.assertEqual(source["env"]["EIRKB_COMMIT"], "${{ steps.eirkb.outputs.commit }}")
        self.assertEqual(source["env"]["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(source["env"]["GIT_ASKPASS"], "/bin/false")
        self.assertEqual(source["env"]["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertNotIn("secrets.", (publication.ROOT / ".github/workflows/deploy.yml").read_text())
        self.assertEqual(workflow["permissions"]["contents"], "read")
        self.assertIn("git init --bare", source["run"])
        self.assertIn("-c credential.helper= -c core.askPass= -c http.extraHeader=", source["run"])
        self.assertIn("fetch --depth=1 --no-tags", source["run"])
        self.assertIn('https://github.com/ecological-interaction/EIRKB.git "$EIRKB_COMMIT"', source["run"])
        build = next(s for s in steps if s["name"] == "Build website")
        self.assertEqual(
            build["env"]["EIRKB_SOURCE"], "${{ github.workspace }}/.sources/EIRKB"
        )
        upload = next(s for s in steps if s["name"] == "Upload website")
        self.assertEqual(upload["with"]["path"], "site")
        self.assertLess(steps.index(source), steps.index(build))
        self.assertLess(steps.index(build), steps.index(upload))


    def test_downloads_and_repeated_imports_preserve_all_source_bytes(self):
        publication.on_config(self.config())
        data = publication.manifest()
        source = publication.source_checkout()
        original = {item["source"]: publication.read_file(source, data["commit"], item) for key in ["documents", "assets", "references"] for item in data[key]}
        results = []
        for _ in range(2):
            generated = {}
            def generate(config, page, **kwargs):
                generated[page] = kwargs["content"]
                return SimpleNamespace(src_uri=page)
            with patch.object(publication.File, "generated", side_effect=generate):
                publication.on_files([], self.config())
            results.append(generated)
        self.assertEqual(results[0], results[1])
        for item in data["documents"]:
            self.assertEqual(results[0][item["page"]], original[item["source"]].decode())
        for item in data["assets"]:
            self.assertEqual(results[0][item["page"]], original[item["source"]])
        self.assertFalse(any(name.endswith(".xlsx") or name.endswith(".py") for name in results[0]))
        self.assertIn('download="EIRKB_Machine_Reference.json"', results[0][publication.MACHINE])
        corpus = json.loads(original["EIRKB_Machine_Reference.json"])
        ids = [row["cells"][0] for row in corpus["collections"]["entities"]["rows"]]
        self.assertEqual(len(ids), 501)
        self.assertEqual(len(set(ids)), 501)
        self.assertIn("R0157", ids)
        self.assertEqual(corpus["collections"]["classifications"]["rows"], [])
        refs = corpus["collections"]["original_reference_records"]["rows"]
        self.assertEqual([row["cells"][0] for row in refs], [f"R{i:03}" for i in range(1, 157)])
        # The README tables are untouched by presentation/link mapping.
        page = SimpleNamespace(file=SimpleNamespace(src_uri=publication.INTRODUCTION))
        rendered = publication.on_page_markdown(original["README.md"].decode(), page)
        self.assertEqual([line for line in rendered.splitlines() if line.startswith("|")], [line for line in original["README.md"].decode().splitlines() if line.startswith("|")])

    def test_complete_historical_anchor_map_and_renamed_register(self):
        publication.on_config(self.config())
        data = publication.manifest()
        item = next(a for a in data["assets"] if a["source"] == "EIRKB_Preservation_Crosswalk.json")
        crosswalk = json.loads(publication.read_file(publication.source_checkout(), data["commit"], item))
        source = next(d for d in data["documents"] if d["source"] == "MASTER_history_theory_ecological_information.md")
        text = publication.read_document(publication.source_checkout(), data["commit"], source)
        rendered = publication.on_page_markdown(text, SimpleNamespace(file=SimpleNamespace(src_uri=publication.HISTORY)))
        for mapping in crosswalk["master_headings_and_anchors"] + crosswalk["master_explicit_anchors"]:
            anchor = mapping["anchor"]
            if anchor != "history-and-theory-of-ecological-information":
                self.assertIn(f'id="{anchor}"', rendered)
            target = publication.EXPECTED[mapping["destination"]].removeprefix(publication.BASE)
            self.assertIn(f"]({target}#{anchor})", rendered)
        legacy = publication.on_page_markdown("# Source tables\n", SimpleNamespace(file=SimpleNamespace(src_uri=publication.LEGACY_REGISTER)))
        self.assertIn('id="eirkb-reference-register"', legacy)
        self.assertIn("](research-protocol.md#guide)", legacy)
        self.assertIn("](changelog.md#migration)", legacy)

    def test_explicit_source_works_without_sibling_repository(self):
        source = publication.source_checkout().resolve()
        manifest_bytes = (publication.ROOT / "publications/eirkb.json").read_bytes()
        with tempfile.TemporaryDirectory(prefix="eirkb-hosted-layout-") as directory:
            root = Path(directory) / "website"
            (root / "publications").mkdir(parents=True)
            (root / "publications/eirkb.json").write_bytes(manifest_bytes)
            self.assertFalse((root.parent / "ecological-information/EIRKB").exists())
            with patch.object(publication, "ROOT", root), patch.dict(os.environ, {"EIRKB_SOURCE": str(source)}):
                self.test_downloads_and_repeated_imports_preserve_all_source_bytes()
                self.test_complete_historical_anchor_map_and_renamed_register()

    def test_allowlists_destinations_and_json_validation_fail_closed(self):
        data = publication.manifest()
        for key in ["documents", "references", "assets"]:
            invalid = dict(data); invalid[key] = []
            with self.assertRaises(ConfigurationError):
                publication.manifest(invalid)
        publication.on_config(self.config())
        for destination in [publication.INTRODUCTION, publication.REGISTER, publication.LEGACY_REGISTER, publication.MACHINE, *publication.ASSETS.values()]:
            with self.assertRaises(ConfigurationError):
                publication.on_files([SimpleNamespace(src_uri=destination)], self.config())
        with patch.object(publication, "read_file", return_value=b"not JSON"), patch.object(publication, "read_document", return_value="# Research"), patch.object(publication.File, "generated", side_effect=lambda cfg, uri, **kw: uri):
            with self.assertRaises(ConfigurationError):
                publication.on_files([], self.config())


if __name__ == "__main__":
    unittest.main()
