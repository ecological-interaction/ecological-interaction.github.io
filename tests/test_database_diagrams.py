"""Integration checks for reviewed, commit-pinned Overview diagrams."""
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from mkdocs.exceptions import ConfigurationError
from scripts import eirkb_publication, eii_publication, gisds_publication
from scripts.publication_diagrams import diagram_markup

MODULES = {"EIRKB": eirkb_publication, "EII": eii_publication, "GISDS": gisds_publication}
COMMITS = {
    "EIRKB": "d5a6a04e03b14903a81adbd347bbf57038b0e7a7",
    "EII": "305fa767d0df1cc7d594f15fc5828eb47639508f",
    "GISDS": "e9bb37e19ee1d7b78f27eadad33d906de80b086e",
}
# Previously approved scientific editions must remain byte-for-byte unchanged.
SCIENTIFIC_HASHES = {
    "EIRKB": {
        "MASTER_history_theory_ecological_information.md": "5a162590b9cd3a117876f798c1356524d8e7a6a551ee4c591d3c271702b4fad1",
        "EIRKB Reference Register.md": "a1a0233f5c1e37d7ce540233425d05cfa2adbc1f929c7857225eeec4ca80fcc1",
    },
    "EII": {
        "EII_Scientific_Reference_Register.md": "ab703e447581478be0aae1ca0530210597063fd46625457f078ed6ac1fc921fb",
        "EII_Machine_Reference.md": "f2c2ebf4fbfc9ec12f3166b95aee0b8856cc85103142726ab60bf2a1897da1f4",
        "EII - Remote Sensing.md": "ca050ccc7c4f09f4da8f30ba420ae2197780943c6fa827298980d4b6853d382d",
    },
    "GISDS": {"GISDS.md": "a6c86e21e2c27cf07c4f8ed6dddfe930b9a3c9f33dc17e20c98e65c140d01aff"},
}


class DatabaseDiagramTests(unittest.TestCase):
    def test_verified_pins_source_integrity_and_verbatim_svg_imports(self):
        for name, module in MODULES.items():
            with self.subTest(repository=name):
                data = module.manifest()
                self.assertEqual(data["commit"], COMMITS[name])
                source = Path(os.environ.get(name + "_SOURCE", str(module.ROOT.parent / "ecological-information" / name)))
                original = {}
                for key in ["documents", "references", "assets"]:
                    for item in data.get(key, []):
                        original[item["source"]] = module.read_file(source, data["commit"], item)
                        if item["source"] in SCIENTIFIC_HASHES[name]:
                            self.assertEqual(item["sha256"], SCIENTIFIC_HASHES[name][item["source"]])
                generated = {}
                def generate(config, page, **kw):
                    generated[page] = kw["content"]
                    return SimpleNamespace(src_uri=page)
                env = {name + "_SOURCE": str(source)}
                with patch.dict(os.environ, env), patch.object(module.File, "generated", side_effect=generate):
                    config = SimpleNamespace(site_dir="site")
                    if name == "EIRKB":
                        module.on_config(config)
                    module.on_files([], config)
                asset = data["assets"][0]
                self.assertEqual(generated[asset["page"]], original[asset["source"]])
                self.assertIsInstance(generated[asset["page"]], bytes)
                self.assertEqual(hashlib.sha256(generated[asset["page"]]).hexdigest(), asset["sha256"])
                diagram = diagram_markup(original["README.md"].decode(), asset["source"])
                if name == "EIRKB":
                    landing = generated[module.INTRODUCTION]
                    self.assertIn(COMMITS[name], landing)
                else:
                    guide = generated[module.GUIDE]
                    self.assertEqual(guide, original["README.md"].decode())
                    self.assertIn(diagram, guide)
                    page = SimpleNamespace(file=SimpleNamespace(src_uri=module.CATALOGUE))
                    with patch.dict(os.environ, env):
                        landing = module.on_page_markdown(generated[module.CATALOGUE], page)
                self.assertIn(diagram, landing)
                self.assertIn(f"[View full-size diagram]({asset['source']})", landing)
                for item in data["documents"]:
                    if item["source"] != "README.md":
                        self.assertEqual(generated[item["page"]], original[item["source"]].decode())

    def test_missing_corrupted_or_unapproved_svg_fails_closed(self):
        for name, module in MODULES.items():
            data = module.manifest()
            item = data["assets"][0]
            for code, content in [(128, b""), (0, b"<svg>corrupted</svg>")]:
                with self.subTest(repository=name, returncode=code), patch.object(
                    module.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=content)
                ):
                    with self.assertRaises(ConfigurationError):
                        module.read_file("source", data["commit"], item)
            for assets in [[], [item | {"page": "unapproved.svg"}], [item | {"sha256": "invalid"}]]:
                with patch.object(Path, "read_text", return_value=json.dumps(data | {"assets": assets})):
                    with self.assertRaises(ConfigurationError):
                        module.manifest()

    def test_source_diagram_block_requires_both_asset_links(self):
        for name in MODULES:
            asset = f"assets/diagrams/{name.lower()}_overview.svg"
            for text in ["# Missing diagram\n", f"# Incomplete\n\n![Diagram]({asset})\n"]:
                with self.assertRaises(ConfigurationError):
                    diagram_markup(text, asset)

    def test_approved_osds_pin_and_unchanged_umbrella_pin(self):
        root = eii_publication.ROOT
        for name, commit in {
            "osds": "059d417ba1c1131ba2a6653bf9f84da76e0ff63c",
            "information": "a820b51c6f5ab695cbdf5c150499897b16a9d216",
        }.items():
            self.assertEqual(json.loads((root / f"publications/{name}.json").read_text())["commit"], commit)
