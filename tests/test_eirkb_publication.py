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
            with patch.object(publication, "read_document", return_value="# Research\n") as read, \
                    patch.object(publication.File, "generated", side_effect=lambda cfg, uri, **kw: uri):
                files = []
                self.assertIs(publication.on_files(files, config), files)
                self.assertEqual(read.call_count, 2)
            self.assertEqual(files, [
                "information/EIRKB/history-and-theory.md",
                publication.REGISTER,
                publication.INTRODUCTION,
            ])
            self.assertIn("EIRKB", config.nav[0]["Information"][1])
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
            self.assertIn("/blob/bbc7c0e755a2504a450272691aed6741af5aa6a7/", result)
            self.assertTrue(result.endswith(f"/{publication.WORKBOOK})"))

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


if __name__ == "__main__":
    unittest.main()
