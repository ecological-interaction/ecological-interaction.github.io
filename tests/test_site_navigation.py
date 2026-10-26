"""Build actual Material output and check branding, routes and disclosure semantics."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from urllib.parse import urljoin, urlsplit

from mkdocs.config import load_config
from mkdocs.commands.build import build

ROOT = Path(__file__).resolve().parents[1]


class Element:
    def __init__(self, tag, attrs=(), parent=None):
        self.tag, self.attrs, self.parent = tag, dict(attrs), parent
        self.children = []

    def all(self, predicate):
        result = [self] if predicate(self) else []
        for child in self.children:
            if isinstance(child, Element):
                result.extend(child.all(predicate))
        return result

    def text(self):
        return ''.join(c.text() if isinstance(c, Element) else c for c in self.children)


class Document(HTMLParser):
    def __init__(self, content):
        super().__init__()
        self.root = Element('document')
        self.stack = [self.root]
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs, self.stack[-1])
        node.parent.children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def has_class(node, name):
    return name in node.attrs.get('class', '').split()


class SiteNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='ei-navigation-test-')
        cls.site = Path(cls.directory.name) / 'site'
        build(load_config(str(ROOT / 'mkdocs.yml'), site_dir=str(cls.site), strict=True))
        cls.document = Document((cls.site / 'index.html').read_text()).root
        cls.nav = cls.document.all(lambda n: n.tag == 'nav' and has_class(n, 'md-nav--primary'))[0]

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_no_sidebar_home_entry_and_header_logo_links_home(self):
        anchors = self.nav.all(lambda n: n.tag == 'a' and n.text().strip() == 'Ecological Interaction')
        self.assertEqual(len(anchors), 0)
        for page in [self.site / 'index.html', self.site / 'information/EII/research-guide/index.html']:
            document = Document(page.read_text()).root
            logos = document.all(lambda n: n.tag == 'a' and has_class(n, 'md-logo'))
            self.assertEqual(len(logos), 2)
            for logo in logos:
                self.assertEqual(logo.attrs['href'], '/')
                self.assertEqual(logo.attrs['aria-label'], 'Ecological Interaction')
                self.assertTrue(logo.all(lambda n: n.tag == 'img'))
        top_list = next(n for n in self.nav.children if isinstance(n, Element) and n.tag == 'ul')
        labels = [n.all(lambda child: child.tag == 'a')[0].text().strip()
                  for n in top_list.children if isinstance(n, Element) and n.tag == 'li']
        self.assertEqual(labels, ['Understanding', 'Information', 'Computation', 'Intelligence', 'Infrastructure', 'Generation'])
        article = self.document.all(lambda n: n.tag == 'article')[0]
        headings = article.all(lambda n: n.tag == 'h1')
        self.assertEqual(len(headings), 1)
        self.assertEqual(headings[0].text(), 'Ecological Interaction')
        self.assertTrue(has_class(headings[0], 'ei-visually-hidden'))
        self.assertEqual([n.text() for n in article.all(lambda n: n.tag == 'h2')], ['Research Layers', 'Projects', 'Development'])
        self.assertIn('Our work is organised into six interconnected research layers.', article.text())
        self.assertEqual(self.document.all(lambda n: n.tag == 'title')[0].text(), 'Ecological Interaction')

    def test_section_indexes_and_child_routes_have_no_duplicate_menu_entries(self):
        expected = {
            '/information/': 'Information',
            '/information/EIRKB/': 'Philosophical Approaches',
            '/information/EIRKB/historic-arc/': 'Historic Arc',
            '/information/EIRKB/intellectual-lineages/': 'Intellectual Lineages',
            '/information/EIRKB/intellectual-map/': 'Intellectual Map',
            '/information/GISDS/': 'Geographic Sources',
            '/information/GISDS/resource-catalogue/': 'GISDS — Resource Catalogue',
            '/information/EII/': 'Indicator Inventory',
            '/information/EII/remote-sensing/': 'EII — Remote Sensing',
            '/information/EII/observational-systems/': 'EII — Observational Systems',
            '/information/OSDS/': 'Observational Systems and Data Sources',
            '/information/OSDS/scientific-reference-register/': 'Scientific Reference Register',
        }
        anchors = self.nav.all(lambda n: n.tag == 'a' and not urlsplit(n.attrs.get('href', '')).fragment)
        for route, label in expected.items():
            matching = [n for n in anchors if urlsplit(urljoin('https://example.test/', n.attrs['href'])).path == route]
            self.assertEqual(len(matching), 1, route)
            self.assertEqual(' '.join(matching[0].text().split()), label)
            self.assertTrue((self.site / route.lstrip('/') / 'index.html').is_file())
        # Corpus and protocol remain reachable at their compatibility routes, outside the menu.
        for name in ['scientific-reference-register', 'machine-reference', 'research-protocol']:
            route = f'/information/EIRKB/{name}/'
            self.assertFalse(any(urlsplit(urljoin('https://example.test/', n.attrs['href'])).path == route for n in anchors))
            self.assertTrue((self.site / route.lstrip('/') / 'index.html').is_file())
        for name in ['research-guide', 'machine-reference']:
            route = f'/information/EII/{name}/'
            self.assertFalse(any(urlsplit(urljoin('https://example.test/', n.attrs['href'])).path == route for n in anchors))
            self.assertTrue((self.site / route.lstrip('/') / 'index.html').is_file())
        self.assertFalse(any(urlsplit(urljoin('https://example.test/', n.attrs['href'])).path == '/information/DRM/' for n in anchors))
        self.assertTrue((self.site / 'information/DRM/index.html').is_file())
        for obsolete in ['Home', 'Overview', 'Introduction', 'Resource catalogue', 'Scientific catalogue']:
            self.assertNotIn(obsolete, [n.text().strip() for n in anchors])

    def test_updated_eirkb_introduction_and_supporting_links(self):
        document = Document((self.site / 'information/EIRKB/index.html').read_text()).root
        article = document.all(lambda n: n.tag == 'article')[0]
        self.assertIn('EIRKB collects references, concepts and people concerned with the history and theory of ecological information', article.text())
        links = article.all(lambda n: n.tag == 'a')
        for label, filename in [('scientific register', 'EIRKB_Scientific_Reference_Register.md'), ('machine reference', 'EIRKB_Machine_Reference.json'), ('research protocol', 'EIRKB_Research_Protocol.md')]:
            self.assertTrue(any(n.text() == label and n.attrs.get('href') == 'https://github.com/ecological-interaction/EIRKB/blob/main/' + filename for n in links))

    def test_pinned_analytical_pages_hide_historical_notes_and_preserve_research_structure(self):
        for route, numbered, territories, subcategories in [
            ('historic-arc', 20, 0, 0),
            ('intellectual-lineages', 14, 0, 0),
            ('intellectual-map', 0, 8, 101),
        ]:
            with self.subTest(route=route):
                html = (self.site / f'information/EIRKB/{route}/index.html').read_text()
                article = Document(html).root.all(lambda n: n.tag == 'article')[0]
                text = article.text()
                self.assertNotRegex(text, r'(?i)\b(your|you|I think|I would|we should|ChatGPT|assistant|next operation|editorial checkpoint|original section)\b')
                self.assertIn('<!-- Historical', html)
                headings = article.all(lambda n: n.tag == 'h3')
                self.assertEqual(sum(bool(re.match(r'^\d+\.', n.text())) for n in headings), numbered)
                self.assertEqual(sum(bool(re.match(r'^[A-H]\.', n.text())) for n in headings), territories)
                self.assertEqual(sum(bool(re.match(r'^[A-H]\d+\.', n.text())) for n in article.all(lambda n: n.tag == 'h4')), subcategories)
                images = article.all(lambda n: n.tag == 'img')
                self.assertEqual(len(images), 1)
                self.assertTrue(images[0].attrs.get('alt'))
                if route == 'intellectual-map':
                    self.assertIn('The map remains provisional', text)
                    self.assertTrue(article.all(lambda n: n.attrs.get('id') == 'preserved-baseline-qualification'))

    def test_native_disclosure_scaffolding_and_accessibility_script_are_present(self):
        containers = self.nav.all(lambda n: n.tag == 'div' and has_class(n, 'md-nav__container'))
        self.assertEqual(len(containers), 6)
        for container in containers:
            title = container.all(lambda n: n.tag == 'a')[0]
            control = container.all(lambda n: n.tag == 'label')[0]
            self.assertTrue(title.text().strip())
            self.assertEqual(control.attrs['tabindex'], '0')
            checkbox = self.nav.all(lambda n: n.tag == 'input' and n.attrs.get('id') == control.attrs['for'])
            self.assertEqual(len(checkbox), 1)
            self.assertEqual(checkbox[0].attrs['type'], 'checkbox')
        scripts = self.document.all(lambda n: n.tag == 'script')
        self.assertTrue(any(n.attrs.get('src', '').endswith('javascripts/navigation-accessibility.js') for n in scripts))
        self.assertTrue((self.site / 'javascripts/navigation-accessibility.js').is_file())

    def test_official_logo_is_loaded_and_preserved_exactly(self):
        images = self.document.all(lambda n: n.tag == 'img')
        matching = [n for n in images if n.attrs.get('src') == 'assets/branding/ecological-interaction-logo.png']
        self.assertTrue(matching)
        asset = self.site / 'assets/branding/ecological-interaction-logo.png'
        self.assertEqual(asset.read_bytes(), (ROOT / 'docs/assets/branding/ecological-interaction-logo.png').read_bytes())
        self.assertEqual(hashlib.sha256(asset.read_bytes()).hexdigest(), 'd265c8181b3c9a1eb4b5eb677ca9b5c99a27a82014de87ad1932157b8494de89')

    def test_disclosure_names_state_and_keyboard_interaction(self):
        node = os.environ.get('EI_TEST_NODE') or shutil.which('node')
        if not node:
            self.skipTest('Set EI_TEST_NODE or put Node.js on PATH to run disclosure interaction coverage.')
        result = subprocess.run([node, '--test', str(ROOT / 'tests/test_navigation_accessibility.js')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
