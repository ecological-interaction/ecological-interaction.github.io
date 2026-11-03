"""Publish approved AMRKB/BIPKB Git objects using the existing pinned-source pattern."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit

from markdown import Markdown
from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {
    'AMRKB': {
        'label': 'Agricultural Modes (AMRKB)',
        'assets': {'assets/diagrams/amrkb_overview.svg'},
        'references': {'AMRKB_Machine_Reference.json', 'AMRKB_Machine_Reference.schema.json',
                       'AMRKB_Research_Protocol.md', 'AMRKB_Source_Editions.json',
                       'AMRKB_Source_Edition_Comparison.json', 'CITATION.cff', 'CHANGELOG.md',
                       'assets/diagrams/amrkb_overview.mmd', 'assets/diagrams/render_amrkb_overview.py'},
    },
    'BIPKB': {
        'label': 'Bioindicators and Phenotypes (BIPKB)',
        'assets': {'assets/diagrams/bipkb_federation.svg', 'assets/diagrams/bipkb_conceptual_reconstruction.svg'},
        'references': {'BIPKB_Machine_Reference.json', 'BIPKB_Machine_Reference.schema.json',
                       'BIPKB_Research_Protocol.md', 'CITATION.cff', 'CHANGELOG.md',
                       'assets/diagrams/bipkb_federation.mmd',
                       'assets/diagrams/bipkb_conceptual_reconstruction.mmd', 'scripts/render_bipkb.py'},
    },
}


def manifest(project):
    if project not in PROJECTS:
        raise ConfigurationError('Unsupported knowledge-base publication.')
    data = json.loads((ROOT / f'publications/{project.lower()}.json').read_text())
    expected = {'README.md': f'information/{project}/index.md',
                f'{project}_Scientific_Reference_Register.md': f'information/{project}/scientific-reference-register.md'}
    assets = {path: f'information/{project}/{path}' for path in PROJECTS[project]['assets']}
    docs, refs, images = (data.get(key, []) for key in ['documents', 'references', 'assets'])
    if (data.get('repository') != f'https://github.com/ecological-interaction/{project}'
            or not re.fullmatch(r'[0-9a-f]{40}', data.get('commit', ''))
            or len(docs) != len(expected) or {x['source']: x['page'] for x in docs} != expected
            or len(refs) != len(PROJECTS[project]['references'])
            or {x['source'] for x in refs} != PROJECTS[project]['references']
            or len(images) != len(assets) or {x['source']: x['page'] for x in images} != assets
            or any(not re.fullmatch(r'[0-9a-f]{64}', x.get('sha256', '')) for x in docs + refs + images)):
        raise ConfigurationError(f'{project}: unapproved repository, commit, source allowlist or checksum.')
    return data


def source_checkout(project):
    value = os.environ.get(f'{project}_SOURCE', '').strip()
    if os.environ.get('GITHUB_ACTIONS', '').lower() == 'true' and not value:
        raise ConfigurationError(f'Hosted builds require {project}_SOURCE.')
    return Path(value or ROOT.parent / f'ecological-information/{project}').expanduser()


def read_file(source, commit, item):
    if not re.fullmatch(r'[0-9a-f]{40}', commit):
        raise ConfigurationError('An immutable full commit SHA is required.')
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(source), 'show',
                             f"{commit}:{item['source']}"], capture_output=True)
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item['sha256']:
        raise ConfigurationError(f"Pinned source unavailable or checksum mismatch: {item['source']}")
    return result.stdout


def source_url(data, path):
    return f"{data['repository']}/blob/{data['commit']}/{quote(path, safe='/')}"


def on_files(files, config):
    # Validate both plans before introducing any generated pages.
    plans = [(project, manifest(project), source_checkout(project)) for project in PROJECTS]
    destinations = {x['page'] for _, data, _ in plans for key in ['documents', 'assets'] for x in data[key]}
    if any(file.src_uri in destinations for file in files):
        raise ConfigurationError('Knowledge-base publication destination already exists.')
    generated = []
    for project, data, source in plans:
        for item in data['references']:
            raw = read_file(source, data['commit'], item)
            if item['source'].endswith('.json'):
                try:
                    json.loads(raw)
                except (ValueError, UnicodeError) as error:
                    raise ConfigurationError(f'{project}: invalid JSON source reference.') from error
        for item in data['documents']:
            generated.append((item['page'], read_file(source, data['commit'], item).decode('utf-8')))
        for item in data['assets']:
            # Preserve source SVG bytes; never execute research code or diagram renderers.
            generated.append((item['page'], read_file(source, data['commit'], item)))
    for path, content in generated:
        files.append(File.generated(config, path, content=content))
    return files


def compatibility_anchors(text):
    """Keep GitHub duplicate-heading URLs alongside MkDocs' native heading IDs."""
    md = Markdown(extensions=['toc', 'tables', 'fenced_code'])
    html = md.convert(text)
    native = re.findall(r'<h[1-6] id="([^"]+)"', html)
    existing = set(re.findall(r'\bid=[\'"]([^\'"]+)', html))
    used = set()
    result = []
    fenced = None
    index = 0
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            if fenced is None:
                fenced = marker[1][0]
            elif marker[1][0] == fenced:
                fenced = None
        heading = re.match(r'^#{1,6} (.+?)\s*$', line) if fenced is None else None
        if heading:
            base = re.sub(r'[^\w -]', '', heading[1].lower()).replace(' ', '-')
            github, suffix = base, 0
            while github in used:
                suffix += 1
                github = f'{base}-{suffix}'
            used.add(github)
            if index >= len(native):
                raise ConfigurationError('Cannot safely map source headings.')
            if github != native[index] and github not in existing:
                alias = f'<a id="{github}"></a>\n\n'
                existing.add(github)
                # MkDocs extracts the page title from the first Markdown element.
                # A compatibility anchor before h1 would incorrectly produce "Index".
                if line.startswith('# '):
                    result.extend([line, '\n', alias])
                    index += 1
                    continue
                result.append(alias)
            index += 1
        result.append(line)
    if index != len(native):
        raise ConfigurationError('Source heading count differs from rendered headings.')
    return ''.join(result)


def map_links(text, project, data):
    documents = {item['source']: Path(item['page']).name for item in data['documents']}
    references = {item['source'] for item in data['references']}
    assets = {item['source'] for item in data['assets']}
    def rewrite(match):
        target = match[2]
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            return match[0]
        path = unquote(url.path)
        suffix = ('?' + url.query if url.query else '') + ('#' + url.fragment if url.fragment else '')
        if path in documents:
            mapped = documents[path]
        elif path in assets:
            mapped = path
        elif path in references:
            mapped = source_url(data, path)
        else:
            raise ConfigurationError(f'{project}: unapproved relative source link: {path}')
        return match[1] + mapped + suffix + match[3]
    # Do not alter code examples or inline source/provenance strings.
    parts = re.split(r'(```[^\n]*\n.*?^```[^\n]*$|~~~[^\n]*\n.*?^~~~[^\n]*$|`[^`\n]+`)', text, flags=re.M | re.S)
    for index in range(0, len(parts), 2):
        parts[index] = re.sub(r'(!?\[[^\]\n]*\]\()([^\s)]+)(\))', rewrite, parts[index])
    return ''.join(parts)


def on_page_markdown(markdown, page, **kwargs):
    uri = page.file.src_uri
    if uri == 'information/index.md':
        for project, config in PROJECTS.items():
            markdown += f"\n\n[Browse {config['label']} and its Scientific Reference]({project}/index.md)\n"
        return markdown
    for project in PROJECTS:
        if uri in {f'information/{project}/index.md', f'information/{project}/scientific-reference-register.md'}:
            return compatibility_anchors(map_links(markdown, project, manifest(project)))
    return markdown
