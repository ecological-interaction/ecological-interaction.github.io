"""Understanding validation and opt-in publication boundaries."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from understanding_validation import (ValidationError, parse_yaml, frontmatter, check_record,
    check_graph, validate_source, check_inventory, contained)
import understanding_publication as publication
from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File, Files
from mkdocs.config import load_config

SOURCE = Path(os.environ.get('UNDERSTANDING_SOURCE', str(publication.DEFAULT_SOURCE)))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((SOURCE / 'architecture/metadata.schema.json').read_text())
        self.example = frontmatter(SOURCE / 'architecture/component-template.md')
        self.example['id'] = 'EU-C-0001'
        self.example['resource_location']['target'] = 'README.md'

    def test_approved_source_and_examples(self):
        domains, records = validate_source(SOURCE)
        self.assertEqual(len(domains), 10)
        self.assertEqual(records, [])

    def test_yaml_rejects_duplicate_keys_and_unsafe_tags(self):
        for text in ('a: 1\na: 2', '!!python/object/apply:os.system [echo unsafe]'):
            with self.subTest(text=text), self.assertRaises((ValidationError, ValueError)):
                parse_yaml(text)

    def test_invalid_formats_vocab_and_required_fields(self):
        for key, value in [('created', '2026-02-30'), ('publication_url', 'not a URI'),
                           ('domains', ['EU-11']), ('functions', []), ('version', 'v1')]:
            item = copy.deepcopy(self.example)
            item[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                check_record(item, SOURCE, self.schema)
        item = copy.deepcopy(self.example)
        del item['title']
        with self.assertRaises(ValidationError):
            check_record(item, SOURCE, self.schema)

    def test_reserved_id_and_path_containment(self):
        item = copy.deepcopy(self.example)
        item['id'] = 'EU-C-0000'
        with self.assertRaises(ValidationError):
            check_record(item, SOURCE, self.schema)
        for target in ('../escape.md', '/etc/passwd', 'https://example.org', 'missing.md'):
            item = copy.deepcopy(self.example)
            item['resource_location']['target'] = target
            with self.subTest(target=target), self.assertRaises(ValidationError):
                check_record(item, SOURCE, self.schema)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'escape').symlink_to('/etc/passwd')
            with self.assertRaises(ValidationError):
                contained(root, 'escape')

    def test_external_target_requires_https(self):
        for target in ('http://example.org', 'file:///etc/passwd', 'https://user:pass@example.org'):
            item = copy.deepcopy(self.example)
            item['resource_location'] = {'kind': 'external', 'target': target}
            with self.subTest(target=target), self.assertRaises(ValidationError):
                check_record(item, SOURCE, self.schema)

    def test_graph_missing_duplicate_cycle_and_versions(self):
        a = copy.deepcopy(self.example)
        b = copy.deepcopy(a)
        b['id'] = 'EU-C-0002'
        check_graph([a, b])
        with self.assertRaises(ValidationError):
            check_graph([a, a])
        a['related_modules'] = ['EU-C-0010']
        with self.assertRaises(ValidationError):
            check_graph([a, b])
        a['related_modules'] = []
        a['prerequisites'] = [{'kind': 'resource', 'resource_id': b['id']}]
        b['prerequisites'] = [{'kind': 'resource', 'resource_id': a['id']}]
        with self.assertRaisesRegex(ValidationError, 'cycle'):
            check_graph([a, b])
        a['prerequisites'], b['prerequisites'] = [], []
        a['programme'] = {'entries': [{'resource_id': b['id'], 'version': '9.0.0'}]}
        with self.assertRaisesRegex(ValidationError, 'version mismatch'):
            check_graph([a, b])
        a['programme']['entries'][0]['version'] = b['version']
        b['programme'] = {'entries': [{'resource_id': a['id'], 'version': a['version']}]}
        with self.assertRaisesRegex(ValidationError, 'Programme inclusion cycle'):
            check_graph([a, b])

    def test_synthetic_programme_shape_is_valid_but_graph_is_not(self):
        example = parse_yaml((SOURCE / 'architecture/programme-example.yaml').read_text())
        check_record(example, SOURCE, self.schema, example=True)
        with self.assertRaisesRegex(ValidationError, 'Unresolved'):
            check_graph([example])

    def test_inventory_has_separate_rules_and_never_catalogue_ready(self):
        inventory = parse_yaml((SOURCE / 'inventory/courseware-candidates.yaml').read_text())
        check_inventory(inventory, self.schema)
        inventory['candidates'][0]['catalogue_ready'] = True
        with self.assertRaises(ValidationError):
            check_inventory(inventory, self.schema)


class PreviewTests(unittest.TestCase):
    def config(self):
        config = load_config(str(ROOT / 'mkdocs.yml'))
        config.plugins._current_plugin = 'understanding-test'
        return config

    def test_preview_watches_the_renamed_source_tree(self):
        server = Mock()
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '1', 'UNDERSTANDING_SOURCE': str(SOURCE), 'GITHUB_ACTIONS': 'false'}):
            self.assertIs(publication.on_serve(server, None, None), server)
        server.watch.assert_called_once_with(str(SOURCE.resolve()))

    def test_default_mode_retains_placeholder_and_navigation(self):
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '0'}):
            config = self.config()
            self.assertEqual(publication.on_config(config)['nav'][0], {'Understanding': 'understanding/index.md'})
            files = Files([File('understanding/index.md', config['docs_dir'], config['site_dir'], True)])
            self.assertIs(publication.on_files(files, config), files)

    def test_hosted_preview_is_rejected(self):
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '1', 'GITHUB_ACTIONS': 'true'}):
            with self.assertRaises(ConfigurationError):
                publication.draft_mode()

    def test_invalid_mode_and_missing_source_fail_closed(self):
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': 'yes'}):
            with self.assertRaises(ConfigurationError):
                publication.draft_mode()
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '1', 'UNDERSTANDING_SOURCE': '/missing-source', 'GITHUB_ACTIONS': 'false'}):
            with self.assertRaises(ConfigurationError):
                publication.on_config(self.config())

    def test_preview_replaces_placeholder_and_has_working_tree_domains(self):
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '1', 'UNDERSTANDING_SOURCE': str(SOURCE), 'GITHUB_ACTIONS': 'false'}):
            config = publication.on_config(self.config())
            self.assertNotEqual(Path(config.site_dir), ROOT / 'site')
            nav = config['nav'][0]['Understanding']
            self.assertEqual(len(nav), 11)
            self.assertEqual(nav[0], 'understanding/index.md')
            files = Files([File('understanding/index.md', config['docs_dir'], config['site_dir'], True)])
            generated = publication.on_files(files, config)
            self.assertEqual(sum(f.src_uri == 'understanding/index.md' for f in generated), 1)
            self.assertEqual(sum(f.src_uri.startswith('understanding/domains/') for f in generated), 10)
            landing = next(f for f in generated if f.src_uri == 'understanding/index.md').content_string
            self.assertEqual(landing.count('class="eu-domain-card"'), 10)
            self.assertIn('reviewed courseware is still in development', landing)
            self.assertNotIn('<input', landing)
            for file in generated:
                self.assertNotIn('/Users/', file.content_string)
            domain = next(f for f in generated if f.src_uri.startswith('understanding/domains/'))
            self.assertIn('../index.md', domain.content_string)
            self.assertFalse(any(f.src_uri.endswith('courseware-candidates.yaml') for f in generated))


class DraftBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mkdocs.commands.build import build
        cls.directory = tempfile.TemporaryDirectory(prefix='understanding-build-')
        cls.site = Path(cls.directory.name)
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '1', 'UNDERSTANDING_SOURCE': str(SOURCE), 'GITHUB_ACTIONS': 'false'}):
            build(load_config(str(ROOT / 'mkdocs.yml'), site_dir=str(cls.site), strict=True))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_domain_and_support_routes_have_resolving_local_links(self):
        from html.parser import HTMLParser
        from urllib.parse import urljoin, urlsplit, unquote
        class Links(HTMLParser):
            def __init__(self, text):
                super().__init__()
                self.links = []
                self.feed(text)
            def handle_starttag(self, tag, attrs):
                if tag == 'a':
                    self.links.append(dict(attrs).get('href', ''))
        pages = list((self.site / 'understanding').rglob('*.html'))
        self.assertEqual(len(pages), 14)
        for page in pages:
            text = page.read_text()
            self.assertNotIn('/Users/', text)
            url = 'https://example.test/' + str(page.relative_to(self.site))
            for link in Links(text).links:
                target = urlsplit(urljoin(url, link))
                if target.netloc != 'example.test':
                    continue
                local = self.site / unquote(target.path).lstrip('/')
                if target.path.endswith('/'):
                    local = local / 'index.html'
                self.assertTrue(local.is_file(), f'{page.name}: {link}')

    def test_navigation_preserves_information_and_has_one_understanding_index(self):
        from test_site_navigation import Document, has_class
        document = Document((self.site / 'understanding/index.html').read_text()).root
        nav = document.all(lambda n: n.tag == 'nav' and has_class(n, 'md-nav--primary'))[0]
        anchors = nav.all(lambda n: n.tag == 'a')
        understanding = [n for n in anchors if n.text().strip() == 'Understanding']
        self.assertEqual(len(understanding), 1)
        self.assertFalse(any(n.text().strip() == 'Overview' for n in anchors))
        self.assertEqual(len(nav.all(lambda n: n.tag == 'div' and has_class(n, 'md-nav__container'))), 6)
        for route in ['information', 'information/EII', 'information/OSDS', 'information/GISDS']:
            self.assertTrue((self.site / route / 'index.html').is_file())


if __name__ == '__main__':
    unittest.main()
