import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from markdown import markdown as render_markdown
from mkdocs.exceptions import ConfigurationError
import yaml
from scripts import eii_publication as publication


class EIIPublicationTests(unittest.TestCase):
    def test_approval_requires_exact_repository_commit_and_allowlists(self):
        original = publication.manifest()
        for change in [{"commit": "main"}, {"repository": "https://example.org/source"}, {"documents": []}, {"references": []}, {"assets": []}, {"documents": original["documents"] + [original["documents"][0]]}, {"assets": [original["assets"][0] | {"page": "other.svg"}]}]:
            with self.subTest(change=change), patch.object(Path, "read_text", return_value=json.dumps(original | change)):
                with self.assertRaises(ConfigurationError): publication.manifest()

    def test_missing_or_modified_source_fails_closed(self):
        for code in [0, 128]:
            with patch.object(publication.subprocess, "run", return_value=SimpleNamespace(returncode=code, stdout=b"changed")):
                with self.assertRaises(ConfigurationError):
                    publication.read_document("source", "a" * 40, {"source": "README.md", "sha256": "0" * 64})
        with self.assertRaises(ConfigurationError):
            publication.read_file("source", "main", {"source": "README.md", "sha256": "0" * 64})

    def test_references_are_checked_but_not_imported_and_import_is_repeatable(self):
        data = publication.manifest(); source = publication.source_checkout()
        original = {item["source"]: publication.read_file(source, data["commit"], item)
                    for group in ["documents", "references", "assets"] for item in data[group]}
        outputs = []
        for _ in range(2):
            generated = {}
            def generate(config, page, **kw):
                generated[page] = kw["content"]
                return SimpleNamespace(src_uri=page)
            with patch.object(publication.File, "generated", side_effect=generate):
                publication.on_files([], SimpleNamespace())
            outputs.append(generated)
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(set(outputs[0]), {*publication.EXPECTED.values(), publication.GUIDE, publication.MACHINE, *publication.ASSETS.values()})
        for item in data["documents"]:
            self.assertEqual(outputs[0][item["page"]], original[item["source"]].decode())
        for item in data["assets"]:
            self.assertEqual(outputs[0][item["page"]], original[item["source"]])
        self.assertIn('EII_Machine_Reference.json', outputs[0][publication.MACHINE])
        self.assertNotIn('fenced JSON', outputs[0][publication.MACHINE])
        self.assertIn('[EII — Ecological Indicator Inventory landing page](index.md)', outputs[0][publication.GUIDE])
        self.assertEqual(len(json.loads(original['EII_Machine_Reference.json'])['indicators']), 235)

    def test_source_mappings_tables_and_single_diagram(self):
        data = publication.manifest(); source = publication.source_checkout()
        for item in data['documents']:
            original = publication.read_document(source, data['commit'], item)
            result = publication.on_page_markdown(original, SimpleNamespace(file=SimpleNamespace(src_uri=item['page'])))
            tables = lambda text: re.findall(r'(?:^\|.*\n)+', text, re.M)
            if item['source'] == 'README.md':
                self.assertEqual(tables(result), tables(original))
                self.assertEqual(result.count('![EII'), 1)
                self.assertEqual(result.count('[View full-size diagram]'), 1)
                self.assertNotIn('[Research guide]', result)
                for name in ['EII_Scientific_Reference_Register.md', 'EII_Machine_Reference.json', 'EII_Research_Protocol.md', 'CITATION.cff']:
                    self.assertIn(publication.source_url(data, name), result)
                self.assertNotIn('/blob/main/', result)
            elif item['source'] == 'EII_Observational_Systems.md':
                self.assertEqual(result, original)
                self.assertIn('No research records or verified source bindings have yet been added.', result)
                self.assertNotIn('|', result)

    def test_links_map_encoded_and_unencoded_names_and_preserve_fragments(self):
        data = publication.manifest()
        science = publication.source_url(data, 'EII_Scientific_Reference_Register.md')
        for target in ['EII - Remote Sensing.md#veg-001', 'EII%20-%20Remote%20Sensing.md#veg-001', '<EII - Remote Sensing.md#veg-001>']:
            result = publication.map_links('[Subset]('+target+')', data)
            self.assertIn('remote-sensing.md#veg-001', result)
        for target in ['EII_Scientific_Reference_Register.md#veg-001', 'EII_Machine_Reference.md#veg-001', publication.REPOSITORY+'/blob/main/EII_Scientific_Reference_Register.md#veg-001']:
            self.assertIn(science+'#veg-001', publication.map_links('[Science]('+target+')', data))
        self.assertEqual(publication.map_links('[Local](#veg-001)', data), '[Local](#veg-001)')

    def test_code_and_historical_provenance_links_are_not_rewritten(self):
        data=publication.manifest()
        for text in ['```markdown\n[Old](EII_Machine_Reference.md#veg-001)\n```\n', '~~~\n[Old](EII_Machine_Reference.md#veg-001)\n~~~\n', '`[Old](EII_Machine_Reference.md#veg-001)`', '    [Old](EII_Machine_Reference.md#veg-001)\n']:
            self.assertEqual(publication.map_links(text,data),text)
        old='[Historical]('+publication.REPOSITORY+'/blob/'+'a'*40+'/EII_Machine_Reference.md)'
        self.assertEqual(publication.map_links(old,data),old)
        self.assertEqual(publication.map_links('Historical path: EII_Machine_Reference.md',data),'Historical path: EII_Machine_Reference.md')

    def test_remote_record_links_target_existing_scientific_anchors(self):
        data=publication.manifest(); source=publication.source_checkout()
        science=next(i for i in data['references'] if i['source']=='EII_Scientific_Reference_Register.md')
        anchors=set(re.findall(r'<a id="([^\"]+)"',publication.read_document(source,data['commit'],science)))
        remote=next(i for i in data['documents'] if i['source']=='EII - Remote Sensing.md')
        original=publication.read_document(source,data['commit'],remote)
        result=publication.on_page_markdown(original,SimpleNamespace(file=SimpleNamespace(src_uri=publication.REMOTE)))
        links=re.findall(re.escape(publication.source_url(data,'EII_Scientific_Reference_Register.md'))+r'#([^)]*)',result)
        self.assertTrue(links)
        self.assertTrue(set(links)<=anchors)
        self.assertEqual(len(re.findall(r'<a id="[a-z]{2,3}-\d{3}"',result)),91)
        # Only the target URI changes; every scientific row and caution remains exact.
        restored=result.replace(publication.source_url(data,'EII_Scientific_Reference_Register.md'),'EII_Scientific_Reference_Register.md')
        self.assertEqual(restored,original)

    def test_compatibility_anchors_are_preserved_without_duplicates(self):
        data=publication.manifest()
        readme=next(i for i in data['documents'] if i['source']=='README.md')
        original=publication.read_document(publication.source_checkout(),data['commit'],readme)
        result=publication.on_page_markdown(original,SimpleNamespace(file=SimpleNamespace(src_uri=publication.CATALOGUE)))
        for text, expected in [(result,publication.LEGACY_LANDING_ANCHORS),(publication.guide_access(data),publication.LEGACY_GUIDE_ANCHORS)]:
            ids=re.findall(r'\bid="([^\"]+)"',render_markdown(text,extensions=['toc','tables','fenced_code']))
            self.assertEqual(len(ids),len(set(ids)))
            self.assertTrue(set(expected)<=set(ids))

    def test_source_checkout_uses_explicit_environment_without_sibling_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'website';root.mkdir()
            source=Path(directory)/'approved';source.mkdir()
            with patch.object(publication,'ROOT',root),patch.dict(os.environ,{'EII_SOURCE':str(source)}):
                self.assertEqual(publication.source_checkout(),source)

    def test_hosted_source_and_all_duplicate_destinations_fail_closed(self):
        with patch.dict(os.environ,{"GITHUB_ACTIONS":"true"},clear=True):
            with self.assertRaises(ConfigurationError): publication.on_files([],SimpleNamespace())
        with patch.dict(os.environ,{},clear=True):
            for destination in {*publication.EXPECTED.values(),*publication.ASSETS.values(),publication.MACHINE,publication.GUIDE}:
                with self.assertRaises(ConfigurationError):
                    publication.on_files([SimpleNamespace(src_uri=destination)],SimpleNamespace())

    def test_invalid_json_reference_fails_closed(self):
        with patch.object(publication,'read_file',return_value=b'invalid JSON'):
            with self.assertRaisesRegex(ConfigurationError,'JSON reference'):
                publication.on_files([],SimpleNamespace())

    def test_other_pages_and_information_navigation_are_preserved(self):
        page=lambda uri:SimpleNamespace(file=SimpleNamespace(src_uri=uri))
        overview='# Authoritative overview\n[GISDS](GISDS/index.md)'
        self.assertEqual(publication.on_page_markdown(overview,page('information/index.md')),overview+publication.OVERVIEW_NAV)
        self.assertEqual(publication.on_page_markdown(overview,page('information/GISDS/index.md')),overview)

    def test_workflow_preserves_deployment_and_public_fetch(self):
        workflow=yaml.load((publication.ROOT/'.github/workflows/deploy.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(workflow['on']['push']['branches'],['main'])
        steps=workflow['jobs']['deploy']['steps'];step=next(s for s in steps if s['name']=='Retrieve approved EII commit anonymously')
        self.assertEqual(step['env']['GIT_CONFIG_GLOBAL'],'/dev/null')
        self.assertEqual(step['env']['GIT_TERMINAL_PROMPT'],'0')
        self.assertIn('"credential.helper="',step['run']);self.assertIn('"--depth=1"',step['run'])
        build=next(s for s in steps if s['name']=='Build website')
        for key in ['EII_SOURCE','EIRKB_SOURCE','INFORMATION_SOURCE','GISDS_SOURCE','OSDS_SOURCE']:self.assertIn(key,build['env'])
