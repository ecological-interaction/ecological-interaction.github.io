"""Publish checksum-verified Understanding Git content; keep drafts explicitly local."""
import html
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import sys
import subprocess
import tempfile
from urllib.parse import urlsplit, quote

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File, Files
from mkdocs.utils import get_relative_url

sys.path.insert(0, str(Path(__file__).resolve().parent))
from understanding_validation import frontmatter, validate_source, contained, check_domain
from understanding_display import SUBJECTS, APPROACHES, approach_icon

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / 'ecological-understanding/ecological-understanding'
SUPPORT = ['architecture/overview.md', 'architecture/interface-specification.md', 'inventory/README.md']

REPOSITORY = 'https://github.com/ecological-interaction/ecological-understanding'
EXPECTED = {
    "README.md": "understanding/index.md",
    "domains/EU-01-ecological-concepts-theory.md": "understanding/domains/EU-01-ecological-concepts-theory.md",
    "domains/EU-02-observation-monitoring.md": "understanding/domains/EU-02-observation-monitoring.md",
    "domains/EU-03-geographic-spatial-understanding.md": "understanding/domains/EU-03-geographic-spatial-understanding.md",
    "domains/EU-04-ecological-indicators-inference.md": "understanding/domains/EU-04-ecological-indicators-inference.md",
    "domains/EU-05-systems-science-relationships.md": "understanding/domains/EU-05-systems-science-relationships.md",
    "domains/EU-06-situated-cultural-knowledge.md": "understanding/domains/EU-06-situated-cultural-knowledge.md",
    "domains/EU-07-computation-intelligence.md": "understanding/domains/EU-07-computation-intelligence.md",
    "domains/EU-08-synthesis-decision-making.md": "understanding/domains/EU-08-synthesis-decision-making.md",
    "domains/EU-09-design-technology-choice.md": "understanding/domains/EU-09-design-technology-choice.md",
    "domains/EU-10-regenerative-systems-practice.md": "understanding/domains/EU-10-regenerative-systems-practice.md",
    "architecture/overview.md": "understanding/architecture/overview.md",
    "architecture/interface-specification.md": "understanding/architecture/interface-specification.md",
    "inventory/README.md": "understanding/inventory/index.md"
}
SOURCE_ONLY = {'PROVENANCE.md', 'inventory/courseware-candidates.yaml'}
_snapshot = None


def manifest():
    try:
        data = json.loads((ROOT / 'publications/understanding.json').read_text())
        entries = data['files']
        if data['repository'] != REPOSITORY or not re.fullmatch(r'[0-9a-f]{40}', data['commit']):
            raise ValueError('Expected the approved repository and a full commit SHA')
        if (len(entries) != len(EXPECTED) or
                {item['source']: item['page'] for item in entries} != EXPECTED or
                any(not re.fullmatch(r'[0-9a-f]{64}', item['sha256']) for item in entries)):
            raise ValueError('Unexpected publication allowlist or checksum')
        return data
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ConfigurationError(f'Invalid Understanding publication manifest: {exc}') from exc


def read_pinned_file(source, commit, item):
    result = subprocess.run(
        ['git', '--no-optional-locks', '-C', str(source), 'show', f"{commit}:{item['source']}"],
        capture_output=True,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item['sha256']:
        raise ConfigurationError('Understanding pinned source unavailable or checksum mismatch; check UNDERSTANDING_SOURCE. No draft fallback is permitted.')
    return result.stdout


def pinned_snapshot():
    global _snapshot
    if _snapshot is not None:
        _snapshot.cleanup()
        _snapshot = None
    data = manifest()
    if os.environ.get('GITHUB_ACTIONS', '').lower() == 'true' and not os.environ.get('UNDERSTANDING_SOURCE', '').strip():
        raise ConfigurationError('Hosted builds require an explicit UNDERSTANDING_SOURCE checkout.')
    snapshot = tempfile.TemporaryDirectory(prefix='understanding-pinned-')
    try:
        root = Path(snapshot.name)
        for item in data['files']:
            content = read_pinned_file(source_root(), data['commit'], item)
            target = root / item['source']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    except Exception:
        snapshot.cleanup()
        raise
    _snapshot = snapshot
    return root


def publication_root():
    if draft_mode():
        return source_root()
    if _snapshot is None:
        raise ConfigurationError('Understanding pinned source has not been validated.')
    return Path(_snapshot.name)


def draft_mode():
    mode = os.environ.get('UNDERSTANDING_DRAFT_PREVIEW', '')
    if mode not in ('', '0', '1'):
        raise ConfigurationError('UNDERSTANDING_DRAFT_PREVIEW must be 0 or 1.')
    if mode == '1' and os.environ.get('GITHUB_ACTIONS', '').lower() == 'true':
        raise ConfigurationError('Hosted builds reject Understanding draft preview.')
    return mode == '1'


def source_root():
    return Path(os.environ.get('UNDERSTANDING_SOURCE', str(DEFAULT_SOURCE))).expanduser().resolve()


def page_for(relative):
    path = Path(relative)
    if path.name == 'README.md':
        path = path.with_name('index.md')
    return 'understanding/' + path.as_posix()


def publication_paths(root):
    # Expand only the linked supporting Markdown closure; raw inventory and provenance
    # are deliberately omitted because they contain local historical/audit paths.
    paths = {'README.md', *SUPPORT}
    paths.update(str(p.relative_to(root)) for p in (root / 'domains').glob('*.md'))
    pending = list(paths)
    while pending:
        rel = pending.pop()
        for target in re.findall(r'\]\(([^\s)]+)\)', (root / rel).read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            child = posixpath.normpath(posixpath.join(posixpath.dirname(rel), url.path))
            contained(root, child)
            if child.endswith('.md') and child != 'PROVENANCE.md' and child not in paths:
                paths.add(child)
                pending.append(child)
    return paths


def transform(text, rel, paths):
    # Keep audit evidence in the source repository; it has no public preview route.
    if draft_mode():
        text = re.sub(r'\[([^\]]+)\]\((?:courseware-candidates\.yaml|PROVENANCE\.md)\)', r'\1 (source-only audit record)', text)
    # Preview copies of internal architecture notes must not expose local paths.
    text = re.sub(r'/Users/[^\s`<>)]+', '[local source path]', text)
    def link(match):
        label, target = match.groups()
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            return match.group(0)
        child = posixpath.normpath(posixpath.join(posixpath.dirname(rel), url.path))
        if child not in paths:
            if not draft_mode():
                if child not in SOURCE_ONLY:
                    raise ConfigurationError(f'Unapproved Understanding link target: {child}')
                destination = REPOSITORY + '/blob/' + manifest()['commit'] + '/' + quote(child, safe='/')
                if url.fragment:
                    destination += '#' + url.fragment
                return f'[{label}]({destination})'
            # Draft-only linked metadata examples are supplied as generated files below.
            destination = 'understanding/' + child
        else:
            destination = page_for(child)
        mapped = posixpath.relpath(destination, posixpath.dirname(page_for(rel)))
        if url.fragment:
            mapped += '#' + url.fragment
        return f'[{label}]({mapped})'
    return re.sub(r'\[([^\]]*)\]\(([^\s)]+)\)', link, text)


def landing_cards(text, root, config):
    cards = []
    landing = File('understanding/index.md', config.docs_dir, config.site_dir, config.use_directory_urls)
    for path in sorted((root / 'domains').glob('*.md')):
        data = frontmatter(path)
        check_domain(data)
        subject, colour = SUBJECTS[data['subject_classification']]
        approach, icon = APPROACHES[data['approach']]
        destination = File(page_for(str(path.relative_to(root))), config.docs_dir,
                           config.site_dir, config.use_directory_urls)
        href = html.escape(get_relative_url(destination.url, landing.url), quote=True)
        cards.append(
            '<article class="eu-domain-card">'
            f'<p class="eu-domain-id">{html.escape(data["domain_id"])}</p>'
            f'<h3><a href="{href}">{html.escape(data["title"])}</a></h3>'
            f'<p class="eu-domain-summary">{html.escape(data["card_summary"])}</p>'
            '<div class="eu-card-footer">'
            f'<span class="eu-approach" data-approach="{data["approach"]}" data-icon="{icon}">'
            f'{approach_icon(data["approach"])}<span>{approach}</span></span>'
            f'<span class="eu-subject" data-subject="{data["subject_classification"]}">'
            f'<span class="eu-dot" style="--eu-dot-colour:{colour}" aria-hidden="true"></span>'
            f'<span>{subject}</span></span></div></article>'
        )
    grid = '<div class="eu-domain-grid">\n' + '\n'.join(cards) + '\n</div>\n\n'
    # Only replace the Markdown table; its surrounding approved text stays intact.
    table = r'(?m)^\| ID \| Thematic domain \|\n(?:^\|[^\n]*\n)+'
    text, count = re.subn(table, lambda _: grid, text, count=1)
    if count != 1:
        raise ConfigurationError('Understanding README requires its domain table.')
    return text


def on_config(config):
    draft = draft_mode()
    if draft:
        if Path(config.site_dir).resolve() == (ROOT / 'site').resolve():
            config.site_dir = str(ROOT / 'site-understanding-preview')
        source = source_root()
        try:
            domains, records = validate_source(source)
        except (ValueError, OSError) as exc:
            raise ConfigurationError(f'Understanding source validation failed: {exc}') from exc
        if records:
            raise ConfigurationError('Resource publication requires a reviewed resource allowlist; this preview supports the foundational framework only.')
    else:
        source = pinned_snapshot()
        domains = sorted((source / 'domains').glob('*.md'))
        for path in domains:
            check_domain(frontmatter(path))
    nav = ['understanding/index.md'] + [
        {frontmatter(path)['title']: page_for(str(path.relative_to(source)))} for path in domains
    ]
    for entry in config['nav']:
        if 'Understanding' in entry:
            entry['Understanding'] = nav
    return config


def on_files(files, config):
    root = publication_root()
    paths = publication_paths(root) if draft_mode() else set(EXPECTED)
    retained = Files([f for f in files if f.src_uri != 'understanding/index.md'])
    destinations = {page_for(p) for p in paths}
    if any(f.src_uri in destinations for f in retained):
        raise ConfigurationError('Duplicate Understanding publication destination.')
    for rel in sorted(paths):
        text = transform((root / rel).read_text(), rel, paths)
        if rel == 'README.md':
            text = landing_cards(text, root, config)
        retained.append(File.generated(config, page_for(rel), content=text))
    # Publish linked metadata examples as downloads, never as catalogue records.
    if draft_mode():
        for rel in ('architecture/metadata.schema.json', 'architecture/programme-example.yaml'):
            retained.append(File.generated(config, 'understanding/' + rel, content=(root / rel).read_bytes()))
    return retained


def on_page_context(context, page, **kwargs):
    if page.file.src_uri.startswith('understanding/'):
        page.meta['description'] = 'Ecological Understanding: research, methods, education and applied practice.'
    return context


def on_serve(server, config, builder):
    if draft_mode():
        server.watch(str(source_root()))
    return server
