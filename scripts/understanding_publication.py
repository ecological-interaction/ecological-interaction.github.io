"""Opt-in local Understanding preview. Production remains on the existing placeholder."""
import html
import os
from pathlib import Path
import posixpath
import re
import sys
from urllib.parse import urlsplit

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File, Files
from mkdocs.utils import get_relative_url

sys.path.insert(0, str(Path(__file__).resolve().parent))
from understanding_validation import frontmatter, validate_source, contained, check_domain
from understanding_display import SUBJECTS, APPROACHES, approach_icon

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT.parent / 'ecological-understanding/ecological-understanding'
SUPPORT = ['architecture/overview.md', 'architecture/interface-specification.md', 'inventory/README.md']


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
            # Linked YAML/JSON examples are supplied as generated files below.
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
    if not draft_mode():
        return config
    # Keep the default draft output separate from the deployable normal build.
    if Path(config.site_dir).resolve() == (ROOT / 'site').resolve():
        config.site_dir = str(ROOT / 'site-understanding-preview')
    source = source_root()
    try:
        domains, records = validate_source(source)
    except (ValueError, OSError) as exc:
        raise ConfigurationError(f'Understanding source validation failed: {exc}') from exc
    if records:
        raise ConfigurationError('Resource publication requires a reviewed resource allowlist; this preview supports the foundational framework only.')
    nav = ['understanding/index.md'] + [
        {frontmatter(path)['title']: page_for(str(path.relative_to(source)))} for path in domains
    ]
    for entry in config['nav']:
        if 'Understanding' in entry:
            entry['Understanding'] = nav
    return config


def on_files(files, config):
    if not draft_mode():
        return files
    root = source_root()
    paths = publication_paths(root)
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
    for rel in ('architecture/metadata.schema.json', 'architecture/programme-example.yaml'):
        retained.append(File.generated(config, 'understanding/' + rel, content=(root / rel).read_bytes()))
    return retained


def on_page_context(context, page, **kwargs):
    if draft_mode() and page.file.src_uri.startswith('understanding/'):
        page.meta['description'] = 'Ecological Understanding: research, methods, education and applied practice.'
    return context


def on_serve(server, config, builder):
    if draft_mode():
        server.watch(str(source_root()))
    return server
