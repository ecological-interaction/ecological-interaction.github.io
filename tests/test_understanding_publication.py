"""Pinned Understanding publication, anonymous retrieval and draft isolation."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mkdocs.config import load_config
from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File, Files
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import understanding_publication as publication
SOURCE = Path(os.environ.get('UNDERSTANDING_SOURCE', str(publication.DEFAULT_SOURCE)))


class PinnedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.data = publication.manifest()

    def tearDown(self):
        if publication._snapshot is not None:
            publication._snapshot.cleanup()
            publication._snapshot = None

    def config(self):
        config = load_config(str(ROOT / 'mkdocs.yml'))
        config.plugins._current_plugin = 'understanding-publication-test'
        return config

    def generate(self, source=SOURCE):
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '0', 'UNDERSTANDING_SOURCE': str(source)}):
            config = publication.on_config(self.config())
            files = Files([File('understanding/index.md', config.docs_dir, config.site_dir, True)])
            return publication.on_files(files, config)

    def test_manifest_hashes_match_exact_commit_and_allowlist(self):
        self.assertEqual(self.data['repository'], 'https://github.com/ecological-interaction/ecological-understanding')
        self.assertRegex(self.data['commit'], r'^[0-9a-f]{40}$')
        self.assertEqual(len(self.data['files']), 14)
        for item in self.data['files']:
            content = subprocess.check_output(['git', '-C', str(SOURCE), 'show', self.data['commit'] + ':' + item['source']])
            self.assertEqual(hashlib.sha256(content).hexdigest(), item['sha256'])

    def test_invalid_repository_ref_allowlist_and_checksum_rejected(self):
        variants = []
        for key, value in [('repository', 'https://example.org/repo'), ('commit', 'main')]:
            data = copy.deepcopy(self.data)
            data[key] = value
            variants.append(data)
        data = copy.deepcopy(self.data)
        data['files'][0]['source'] = '../README.md'
        variants.append(data)
        data = copy.deepcopy(self.data)
        data['files'][0]['page'] = 'information/index.md'
        variants.append(data)
        data = copy.deepcopy(self.data)
        data['files'][0]['sha256'] = 'not-a-checksum'
        variants.append(data)
        data = copy.deepcopy(self.data)
        data['files'].append(data['files'][0])
        variants.append(data)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'publications').mkdir()
            for data in variants:
                (root / 'publications/understanding.json').write_text(json.dumps(data))
                with self.subTest(data=data), patch.object(publication, 'ROOT', root), self.assertRaises(ConfigurationError):
                    publication.manifest()

    def test_missing_commit_and_checksum_failure_never_fall_back(self):
        for key in ('commit', 'checksum'):
            data = copy.deepcopy(self.data)
            if key == 'commit':
                data['commit'] = '0' * 40
            else:
                data['files'][0]['sha256'] = '0' * 64
            with self.subTest(key=key), patch.object(publication, 'manifest', return_value=data), patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '0', 'UNDERSTANDING_SOURCE': str(SOURCE)}):
                with self.assertRaisesRegex(ConfigurationError, 'No draft fallback'):
                    publication.on_config(self.config())
                self.assertIsNone(publication._snapshot)

    def test_uncommitted_working_tree_changes_cannot_enter_production(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(SOURCE), str(source)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(source), 'checkout', '--quiet', '--detach', self.data['commit']], check=True)
            (source / 'README.md').write_text('UNCOMMITTED CONTENT MUST NEVER BE PUBLISHED')
            domain = source / 'domains/EU-01-ecological-concepts-theory.md'
            domain.write_text(domain.read_text().replace('subject_classification: concept', 'subject_classification: application'))
            files = self.generate(source)
            text = next(f for f in files if f.src_uri == 'understanding/index.md').content_string
            self.assertNotIn('UNCOMMITTED CONTENT', text)
            self.assertEqual(text.count('class="eu-domain-card"'), 10)
            with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '1', 'UNDERSTANDING_SOURCE': str(source), 'GITHUB_ACTIONS': 'false'}):
                with self.assertRaises(ConfigurationError):
                    publication.on_config(self.config())

    def test_bare_source_is_supported_and_snapshot_matches_git(self):
        with tempfile.TemporaryDirectory() as directory:
            bare = Path(directory) / 'source.git'
            subprocess.run(['git', 'clone', '--quiet', '--bare', '--no-hardlinks', str(SOURCE), str(bare)], check=True, capture_output=True)
            self.generate(bare)
            root = publication.publication_root()
            for item in self.data['files']:
                self.assertEqual(hashlib.sha256((root / item['source']).read_bytes()).hexdigest(), item['sha256'])

    def test_production_has_no_examples_local_paths_or_duplicate_destinations(self):
        files = self.generate()
        uris = [f.src_uri for f in files]
        self.assertEqual(len(uris), len(set(uris)))
        self.assertEqual(len(uris), 14)
        self.assertFalse(any(f.endswith(('.yaml', '.json')) for f in uris))
        for file in files:
            self.assertNotIn('/Users/', file.content_string)
        landing = next(f for f in files if f.src_uri == 'understanding/index.md').content_string
        self.assertIn(publication.REPOSITORY + '/blob/' + self.data['commit'] + '/PROVENANCE.md', landing)
        inventory = next(f for f in files if f.src_uri == 'understanding/inventory/index.md').content_string
        self.assertIn('/blob/' + self.data['commit'] + '/inventory/courseware-candidates.yaml', inventory)
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '0'}):
            with self.assertRaises(ConfigurationError):
                publication.transform('[unapproved](missing.md)', 'README.md', set(publication.EXPECTED))

    def test_hosted_build_requires_explicit_source_and_rejects_draft(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'UNDERSTANDING_DRAFT_PREVIEW': '0', 'UNDERSTANDING_SOURCE': ''}):
            with self.assertRaisesRegex(ConfigurationError, 'explicit UNDERSTANDING_SOURCE'):
                publication.on_config(self.config())
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'UNDERSTANDING_DRAFT_PREVIEW': '1'}):
            with self.assertRaisesRegex(ConfigurationError, 'Hosted builds reject'):
                publication.on_config(self.config())

    def test_workflow_fetches_exact_commit_anonymously_and_builds_production(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/deploy.yml').read_text())
        steps = workflow['jobs']['deploy']['steps']
        step = next(s for s in steps if s.get('name') == 'Retrieve approved Understanding commit anonymously')
        for key in ('GIT_TERMINAL_PROMPT', 'GIT_ASKPASS', 'GIT_CONFIG_NOSYSTEM', 'GIT_CONFIG_GLOBAL'):
            self.assertIn(key, step['env'])
        for text in ['publications/understanding.json', publication.REPOSITORY, 'credential.helper=', 'http.extraHeader=', 'data["commit"]', 'checkout', '--detach']:
            self.assertIn(text, step['run'])
        self.assertNotIn('secrets.', step['run'])
        for name in ('Test publication import', 'Build website'):
            env = next(s for s in steps if s.get('name') == name)['env']
            self.assertEqual(env['UNDERSTANDING_DRAFT_PREVIEW'], '0')
            self.assertEqual(env['UNDERSTANDING_SOURCE'], '${{ github.workspace }}/.sources/ecological-understanding')


class ProductionBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from mkdocs.commands.build import build
        cls.directory = tempfile.TemporaryDirectory(prefix='understanding-production-')
        cls.site = Path(cls.directory.name)
        with patch.dict(os.environ, {'UNDERSTANDING_DRAFT_PREVIEW': '0', 'UNDERSTANDING_SOURCE': str(SOURCE)}):
            config = load_config(str(ROOT / 'mkdocs.yml'), site_dir=str(cls.site), strict=True)
            build(config)
            cls.hook = next(h for h in config['hooks'].values() if Path(h.__file__).name == 'understanding_publication.py')

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_production_cards_routes_and_source_metadata(self):
        from test_site_navigation import Document, has_class
        from understanding_validation import frontmatter
        document = Document((self.site / 'understanding/index.html').read_text()).root
        cards = document.all(lambda n: n.tag == 'article' and has_class(n, 'eu-domain-card'))
        self.assertEqual(len(cards), 10)
        root = self.hook.publication_root()
        for path, card in zip(sorted((root / 'domains').glob('*.md')), cards):
            data = frontmatter(path)
            self.assertIn(data['card_summary'], card.text())
            subject = card.all(lambda n: n.attrs.get('data-subject') == data['subject_classification'])
            approach = card.all(lambda n: n.attrs.get('data-approach') == data['approach'])
            self.assertEqual(len(subject), 1)
            self.assertEqual(len(approach), 1)
            self.assertTrue((self.site / 'understanding/domains' / path.stem / 'index.html').is_file())
        self.assertFalse((self.site / 'understanding/architecture/programme-example.yaml').exists())
        self.assertTrue((self.site / 'information/EII/index.html').is_file())
        self.assertEqual(len(list((self.site / 'understanding').rglob('*.html'))), 14)


    def test_all_production_local_links_resolve(self):
        from test_site_navigation import Document
        from urllib.parse import urljoin, urlsplit, unquote
        for page in (self.site / 'understanding').rglob('*.html'):
            text = page.read_text()
            self.assertNotIn('/Users/', text)
            document = Document(text).root
            url = 'https://example.test/' + str(page.relative_to(self.site))
            for anchor in document.all(lambda n: n.tag == 'a'):
                target = urlsplit(urljoin(url, anchor.attrs.get('href', '')))
                if target.netloc != 'example.test':
                    continue
                local = self.site / unquote(target.path).lstrip('/')
                if target.path.endswith('/'):
                    local = local / 'index.html'
                self.assertTrue(local.is_file(), f'{page}: {target.path}')


if __name__ == '__main__':
    unittest.main()
