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
    "EIRKB": "5c31c6599e928527417266132a242ee2095610de",
    "EII": "76ea70afb2e755a541c63bd24cdade7de9c1f2ce",
    "GISDS": "9ff8c1adb3929c2e4a619a1dc052f9764738c33f",
}
# Previously approved scientific editions must remain byte-for-byte unchanged.
SCIENTIFIC_HASHES = {
    "EIRKB": {'README.md': '5e9cd6d7114c68f847c338f8297e5f490a3f5a61611b6078a198a2ea60118c26', 'EIRKB_Scientific_Reference_Register.md': 'caa968d112c498839adb28ad241b0eed8795a869f5af628a2c581ce27b6bdb8e', 'EIRKB_Research_Protocol.md': '2549cdb644fed485f491db5cc917eda654d061199943a57b7fdf2ed10ebca73d', 'A01_Historic_Arc.md': '8a27ab8c040d6589667f2b3168200ed5422a636a168f8576b997e577b117cdfc', 'A02_Intellectual_Lineages.md': 'b298385bf3aa9db8e07e8513b8cd516fd102539adbc66b264e104598f6f1e1cc', 'A03_Intellectual_Map.md': 'db8ed76d100a08f8f77eff03e93c59029f17f5d764319ac7af17d238da5a305a', 'MASTER_history_theory_ecological_information.md': '97a43d8a9feacaa9f3a5f8bca3b1ed7f0d2e0ac9e9d48fe568ea0adb5bf9b359', 'CHANGELOG.md': 'aa26386d7391a922f521269405720cab444b68b9af122b997f9741dd8989ac13', 'assets/diagrams/eirkb_federation.svg': '1bea9c902dbb32c80e34a3841d9305de4b91ae3d60bd12dd073fd846c7963445', 'assets/diagrams/eirkb_overview.svg': '30995aeebdb65a7898a66eed7db47b8eaad852d119e31b6c8e8d84a590c12471', 'EIRKB_Machine_Reference.json': 'f2427babb53954c57a42ce454d8165ad1f697ceaeae12ec3d97c7b3fd2831da9', 'EIRKB_Machine_Reference.schema.json': '2dbf52b1d1463e556207c42cd10d857ca190cd09351156e1de79906c13b39e62', 'EIRKB_Preservation_Crosswalk.json': 'a0bb224c7085e2351665a82f80fc1a689f17759560e4544879ba37d144488cd8', 'CITATION.cff': '589b097cbaad8b6c495d2193f522a134696c0bf46a3ec1a27b1bd93298915bd5'},
    "EII": {'README.md': '60b8dd67510750446b7026af9f3da2fd92225428438b8d48ca1e2f6101b88c96', 'EII - Remote Sensing.md': 'd826e12a3ad2e3a84ef32417f907efa7f76c153268f3b3545a23041f5dccc6d8', 'EII_Observational_Systems.md': '20b3eee992a9e31afe8252d7e0dbfdc801d707c6994da54f5fcd3c4bc012dfc3', 'EII_Scientific_Reference_Register.md': '67932a9cd44ec2a680a3fd19d64e86b494ad5e7c1cb38e09ee2054ecf51da2d7', 'EII_Machine_Reference.json': '0446dd4d25b84ff9f7556775bad692b4b1152482bf140ef4dcdfd4100a839689', 'EII_Research_Protocol.md': 'c3a8f6be22e6a2d191c70da78525f5d3b6ec6e32d8aa886d96ebb74c17999dc5', 'EII_Machine_Reference.md': '4db2d6891a0f82dd08d49dfbc1345511658866e9715a8783d9738d3aa0bb6423', 'CITATION.cff': '38376b7141e97256c21a06b263e8b21132b2c3b8f4671a8c775c3ec36c4abdd9', 'CHANGELOG.md': 'cd5df1368a83954dbecb6d05e15cbc147092b5d2e01ec9f945b819ae67982c7d', 'EII_Machine_Reference.schema.json': 'fbc921f317225715dbf1b20dde79f980fe80a83f5acb44be2e20294a7da7a002', 'EII_Preservation_Crosswalk.json': 'af369978a5d29ec8bd2792efeab74f4cd98e850536ddc0ab96fe2d9e65ebdc5d', 'assets/diagrams/eii_overview.mmd': 'ceb2a37e311030feef8ce9c60f1dd36afb4a4c6b82a1978e7dc65eb98206b524', 'assets/diagrams/render_eii_overview.py': '8151c4d415aa2780222a2e189b6a3c1d4cb8468dce5625eec878308e9995ba57', 'assets/diagrams/eii_overview.svg': 'ce8fd6d5bbca54475d3e9ace515644e77df4a1a4f8cc9e589f226fad8905a349'},
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
                if name in {"EIRKB", "EII"}:
                    landing = generated[module.INTRODUCTION if name == "EIRKB" else module.CATALOGUE]
                    self.assertEqual(landing, original["README.md"].decode())
                    self.assertIn(asset["source"], landing)
                    for item in data["assets"]:
                        self.assertEqual(generated[item["page"]], original[item["source"]])
                elif name == "GISDS":
                    landing = module.on_page_markdown(generated[module.GUIDE], SimpleNamespace(file=SimpleNamespace(src_uri=module.GUIDE)))
                    self.assertIn(f"]({asset['source']})", landing)
                    self.assertIn(f"[View full-size diagram]({asset['source']})", landing)
                    self.assertNotIn("gisds_overview.svg", module.on_page_markdown(generated[module.CATALOGUE], SimpleNamespace(file=SimpleNamespace(src_uri=module.CATALOGUE))))
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
