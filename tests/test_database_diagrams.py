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
    "EIRKB": "ec68ea37814adbc5903ccb0c9c30719045d07a82",
    "EII": "305fa767d0df1cc7d594f15fc5828eb47639508f",
    "GISDS": "9ff8c1adb3929c2e4a619a1dc052f9764738c33f",
}
# Previously approved scientific editions must remain byte-for-byte unchanged.
SCIENTIFIC_HASHES = {
    "EIRKB": {'README.md': 'e6854a9f35424811c826fcd1c485bb099f2819b175a321a53d5262d0cc3beabf', 'EIRKB_Scientific_Reference_Register.md': 'caa968d112c498839adb28ad241b0eed8795a869f5af628a2c581ce27b6bdb8e', 'EIRKB_Research_Protocol.md': '2549cdb644fed485f491db5cc917eda654d061199943a57b7fdf2ed10ebca73d', 'A01_Historic_Arc.md': '95c37d1b92093ab949951bd6c19de2da3e7136fbea1ff984a6047c91f85221b2', 'A02_Intellectual_Lineages.md': '15de0036c22a3f4f3be2518b50ed6cbde58dfc3dda5a350f9eabf034f02cb6e9', 'A03_Intellectual_Map.md': 'c1c585adf041d9bf3902ea815955769fd263605e3d2db504c84b10688be35499', 'MASTER_history_theory_ecological_information.md': '97a43d8a9feacaa9f3a5f8bca3b1ed7f0d2e0ac9e9d48fe568ea0adb5bf9b359', 'CHANGELOG.md': 'aa26386d7391a922f521269405720cab444b68b9af122b997f9741dd8989ac13', 'assets/diagrams/eirkb_federation.svg': '1bea9c902dbb32c80e34a3841d9305de4b91ae3d60bd12dd073fd846c7963445', 'assets/diagrams/eirkb_overview.svg': '30995aeebdb65a7898a66eed7db47b8eaad852d119e31b6c8e8d84a590c12471', 'EIRKB_Machine_Reference.json': 'f2427babb53954c57a42ce454d8165ad1f697ceaeae12ec3d97c7b3fd2831da9', 'EIRKB_Machine_Reference.schema.json': '2dbf52b1d1463e556207c42cd10d857ca190cd09351156e1de79906c13b39e62', 'EIRKB_Preservation_Crosswalk.json': 'a0bb224c7085e2351665a82f80fc1a689f17759560e4544879ba37d144488cd8', 'CITATION.cff': '589b097cbaad8b6c495d2193f522a134696c0bf46a3ec1a27b1bd93298915bd5'},
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
                if name == "EIRKB":
                    landing = generated[module.INTRODUCTION]
                    self.assertEqual(landing, original["README.md"].decode())
                    self.assertIn("eirkb_federation.svg", landing)
                    for item in data["assets"]:
                        self.assertEqual(generated[item["page"]], original[item["source"]])
                elif name == "GISDS":
                    landing = module.on_page_markdown(generated[module.GUIDE], SimpleNamespace(file=SimpleNamespace(src_uri=module.GUIDE)))
                    self.assertIn(f"]({asset['source']})", landing)
                    self.assertIn(f"[View full-size diagram]({asset['source']})", landing)
                    self.assertNotIn("gisds_overview.svg", module.on_page_markdown(generated[module.CATALOGUE], SimpleNamespace(file=SimpleNamespace(src_uri=module.CATALOGUE))))
                else:
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
            "osds": "48b5d7f131ae4b86557d4a7b58a1371cacd3cd6c",
            "information": "a820b51c6f5ab695cbdf5c150499897b16a9d216",
        }.items():
            self.assertEqual(json.loads((root / f"publications/{name}.json").read_text())["commit"], commit)
