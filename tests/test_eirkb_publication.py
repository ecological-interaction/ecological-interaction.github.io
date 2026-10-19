import hashlib
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mkdocs.exceptions import ConfigurationError

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

    def test_default_build_does_not_read_private_sources_or_advertise_pages(self):
        with patch.dict(os.environ, {}, clear=True):
            config = publication.on_config(self.config())
            with patch.object(publication, "read_document") as read:
                files = []
                self.assertIs(publication.on_files(files, config), files)
                read.assert_not_called()
            self.assertEqual(config.nav, [
                {"Information": [{"Overview": "information/index.md"}]}
            ])
            page = SimpleNamespace(file=SimpleNamespace(src_uri="information/index.md"))
            self.assertEqual(publication.on_page_markdown(publication.MARKER, page), "")

    def test_github_actions_cannot_enable_the_local_preview(self):
        with patch.dict(os.environ, {"EIRKB_PREVIEW": "1", "GITHUB_ACTIONS": "true"}):
            with self.assertRaises(ConfigurationError):
                publication.on_config(self.config())

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

    def test_workbook_link_resolves_without_importing_the_private_asset(self):
        with patch.dict(os.environ, {"EIRKB_PREVIEW": "1", "GITHUB_ACTIONS": "false"}):
            publication.on_config(self.config())
            page = SimpleNamespace(file=SimpleNamespace(src_uri=publication.REGISTER))
            text = f"[Source workbook]({publication.WORKBOOK})"
            result = publication.on_page_markdown(text, page)
            self.assertIn("/blob/bbc7c0e755a2504a450272691aed6741af5aa6a7/", result)
            self.assertTrue(result.endswith(f"/{publication.WORKBOOK})"))


if __name__ == "__main__":
    unittest.main()
