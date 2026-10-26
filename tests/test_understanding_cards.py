"""Approved domain metadata, accessible cards and both MkDocs URL modes."""
import copy
from html.parser import HTMLParser
import os
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from mkdocs.config import load_config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import understanding_publication as publication
from understanding_validation import frontmatter, check_domain, ValidationError, check_record
from understanding_display import SUBJECTS, APPROACHES, approach_icon

SOURCE = Path(os.environ.get('UNDERSTANDING_SOURCE', str(publication.DEFAULT_SOURCE)))
EXPECTED = [
    ('concept', 'systems'), ('biology', 'technology'), ('geography', 'computation'),
    ('ecology', 'computation'), ('ecology', 'systems'), ('practice', 'systems'),
    ('ecology', 'computation'), ('practice', 'systems'), ('practice', 'design'), ('ecology', 'design'),
]


class CardParser(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.cards = []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and attrs.get('class') == 'eu-domain-card':
            self.cards.append({'tags': [], 'text': ''})
        if self.cards:
            self.cards[-1]['tags'].append((tag, attrs))
    def handle_data(self, text):
        if self.cards:
            self.cards[-1]['text'] += text


class CardTests(unittest.TestCase):
    def render(self, directory_urls=True):
        config = load_config(str(ROOT / 'mkdocs.yml'), use_directory_urls=directory_urls)
        return publication.landing_cards((SOURCE / 'README.md').read_text(), SOURCE, config)

    def test_final_source_mapping_and_display_vocabulary(self):
        self.assertEqual(SUBJECTS, {
            'geography': ('Geography', '#2563EB'), 'ecology': ('Ecology', '#15803D'),
            'biology': ('Biology', '#D97706'), 'concept': ('Concept', '#7C3AED'),
            'practice': ('Practice', '#0F766E'),
        })
        self.assertEqual(APPROACHES, {
            'systems': ('Systems', 'graph-outline'), 'technology': ('Technology', 'cog-outline'),
            'computation': ('Computation', 'code-braces'), 'design': ('Design', 'pencil-ruler'),
        })
        for i, (path, expected) in enumerate(zip(sorted((SOURCE / 'domains').glob('*.md')), EXPECTED), 1):
            data = frontmatter(path)
            self.assertEqual(data['domain_id'], f'EU-{i:02}')
            self.assertEqual((data['subject_classification'], data['approach']), expected)
            check_domain(data)

    def test_reject_unknown_categories_missing_summary_and_long_descriptions(self):
        data = frontmatter(next((SOURCE / 'domains').glob('*.md')))
        for key, value in [('subject_classification', 'application'), ('approach', '../../unknown'),
                           ('card_summary', 'This domain investigates ecosystems.'),
                           ('card_summary', 'One sentence. Another sentence. A third sentence.'),
                           ('card_summary', '   ')]:
            item = copy.deepcopy(data)
            item[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                check_domain(item)
        del data['card_summary']
        with self.assertRaises(ValidationError):
            check_domain(data)

    def test_render_order_titles_metadata_and_footer(self):
        text = self.render()
        cards = CardParser(text).cards
        self.assertEqual(len(cards), 10)
        for path, expected, card in zip(sorted((SOURCE / 'domains').glob('*.md')), EXPECTED, cards):
            data = frontmatter(path)
            tags = card['tags']
            self.assertEqual(tags[1], ('p', {'class': 'eu-domain-id'}))
            self.assertIn(data['title'], card['text'])
            self.assertIn(data['card_summary'], card['text'])
            self.assertNotIn('Foundational outline', card['text'])
            approach = next(a for t, a in tags if a.get('class') == 'eu-approach')
            subject = next(a for t, a in tags if a.get('class') == 'eu-subject')
            self.assertEqual(approach['data-approach'], expected[1])
            self.assertEqual(approach['data-icon'], APPROACHES[expected[1]][1])
            self.assertEqual(subject['data-subject'], expected[0])
            dot = next(a for t, a in tags if a.get('class') == 'eu-dot')
            self.assertEqual(dot['style'], '--eu-dot-colour:' + SUBJECTS[expected[0]][1])
            self.assertIn(('svg', next(a for t, a in tags if t == 'svg')), tags)
            svg = next(a for t, a in tags if t == 'svg')
            self.assertEqual(svg['aria-hidden'], 'true')
            self.assertEqual(svg['focusable'], 'false')
            classes = [a.get('class') for _, a in tags]
            self.assertLess(classes.index('eu-approach'), classes.index('eu-subject'))

    def test_links_follow_both_mkdocs_url_modes(self):
        for directory_urls in (True, False):
            cards = CardParser(self.render(directory_urls)).cards
            for path, card in zip(sorted((SOURCE / 'domains').glob('*.md')), cards):
                link = next(a for t, a in card['tags'] if t == 'a')
                suffix = '/' if directory_urls else '.html'
                self.assertEqual(link['href'], 'domains/' + path.stem + suffix)
                self.assertNotIn('target', link)

    def test_source_text_is_escaped_and_unknown_icons_rejected(self):
        original = publication.frontmatter
        def injected(path):
            data = original(path)
            data['title'] = '<img src=x onerror="alert(1)">'
            data['card_summary'] = '<script>alert(1)</script> & "quoted"'
            return data
        with patch.object(publication, 'frontmatter', side_effect=injected):
            rendered = self.render()
        self.assertNotIn('<script>', rendered)
        self.assertNotIn('<img', rendered)
        self.assertIn('&lt;script&gt;', rendered)
        self.assertIn('&amp;', rendered)
        with self.assertRaises(KeyError):
            approach_icon('unknown')
        for approach in APPROACHES:
            self.assertEqual(ET.fromstring(approach_icon(approach)).tag, '{http://www.w3.org/2000/svg}svg')

    def test_readme_order_and_github_table_are_preserved(self):
        source = (SOURCE / 'README.md').read_text()
        self.assertEqual(re.findall(r'^## (.+)$', source, re.M), [
            'Ten thematic knowledge domains', 'Objectives and principles', 'Four framework functions',
            'Components, modules and classification', 'Courses and programmes',
            'Relationship to Ecological Interaction', 'Development and resources',
        ])
        self.assertEqual(len(re.findall(r'^\| EU-\d\d \|', source, re.M)), 10)
        self.assertIn('subject classification and approach', source)
        rendered = self.render()
        self.assertNotIn('| ID | Thematic domain |', rendered)
        self.assertLess(rendered.index('eu-domain-grid'), rendered.index('## Objectives and principles'))
        self.assertNotIn('## Resource catalogue', rendered)

    def test_display_fields_do_not_extend_component_schema(self):
        import json
        schema = json.loads((SOURCE / 'architecture/metadata.schema.json').read_text())
        data = frontmatter(SOURCE / 'architecture/component-template.md')
        for key, value in [('card_summary', 'A short summary.'), ('subject_classification', 'ecology'), ('approach', 'systems')]:
            item = copy.deepcopy(data)
            item[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                check_record(item, SOURCE, schema, example=True)


if __name__ == '__main__':
    unittest.main()
