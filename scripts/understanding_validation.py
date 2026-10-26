"""Validate source-owned Understanding documents; examples never enter the catalogue."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, unquote

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from understanding_display import SUBJECTS, APPROACHES

DOMAINS = [f'EU-{i:02}' for i in range(1, 11)]
RESERVED = {'EU-C-0000', 'EU-C-9999'}


class ValidationError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    pass


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValidationError(f'Duplicate YAML key: {key}')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def parse_yaml(text):
    try:
        return yaml.load(text, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ValidationError(str(exc)) from exc


def frontmatter(path):
    text = path.read_text(encoding='utf-8')
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
    if not match:
        raise ValidationError(f'Missing front matter: {path.name}')
    data = parse_yaml(match[1])
    if not isinstance(data, dict):
        raise ValidationError('Front matter must be an object')
    return data


def check_schema(data, schema):
    # The schema is local and contains no external references.
    Draft202012Validator.check_schema(schema)
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(data))
    if errors:
        raise ValidationError('; '.join(f'{list(e.path)}: {e.message}' for e in errors))


def contained(root, target, must_exist=True):
    if not isinstance(target, str) or not target or '\\' in target or Path(target).is_absolute():
        raise ValidationError('Expected a repository-relative path')
    path = (root / target).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValidationError(f'Path escapes source: {target}')
    if must_exist and not path.is_file():
        raise ValidationError(f'Missing local file: {target}')
    return path


def https_url(value):
    try:
        url = urlsplit(value)
        valid = url.scheme == 'https' and url.hostname and not url.username and not url.password
    except ValueError:
        valid = False
    if not valid:
        raise ValidationError(f'Expected an HTTPS URL: {value}')


def check_record(data, root, schema, example=False):
    check_schema(data, schema)
    if not example and data['id'] in RESERVED:
        raise ValidationError(f'Reserved example ID: {data["id"]}')
    location = data['resource_location']
    if location['kind'] == 'local':
        contained(root, location['target'], must_exist=not example)
    else:
        https_url(location['target'])
    for ref in data['source_references']:
        for field in ('url', 'repository'):
            if ref[field] is not None:
                https_url(ref[field])
    if data.get('publication_url'):
        https_url(data['publication_url'])
    if data['updated'] < data['created']:
        raise ValidationError('Updated date precedes creation')
    if data.get('reviewed_on') and data['reviewed_on'] < data['created']:
        raise ValidationError('Review date precedes creation')


def acyclic(edges, label):
    active, done = set(), set()
    def visit(node):
        if node in active:
            raise ValidationError(f'{label} cycle at {node}')
        if node in done:
            return
        active.add(node)
        for other in edges.get(node, []):
            visit(other)
        active.remove(node)
        done.add(node)
    for node in edges:
        visit(node)


def check_graph(records):
    by_id = {}
    for record in records:
        identifier = record['id']
        if identifier in by_id:
            raise ValidationError(f'Duplicate resource ID: {identifier}')
        by_id[identifier] = record
    prerequisites, programmes = {}, {}
    for identifier, record in by_id.items():
        deps = [p['resource_id'] for p in record['prerequisites'] if p['kind'] == 'resource']
        members = record.get('programme', {}).get('entries', [])
        references = deps + record['related_modules'] + [p['resource_id'] for p in members]
        for target in references:
            if target not in by_id:
                raise ValidationError(f'Unresolved reference: {identifier} → {target}')
            if target == identifier:
                raise ValidationError(f'Self reference: {identifier}')
        for member in members:
            if by_id[member['resource_id']]['version'] != member['version']:
                raise ValidationError(f'Programme member version mismatch: {member["resource_id"]}')
        prerequisites[identifier] = deps
        programmes[identifier] = [m['resource_id'] for m in members]
    acyclic(prerequisites, 'Prerequisite')
    acyclic(programmes, 'Programme inclusion')


def check_inventory(data, resource_schema):
    props = resource_schema['properties']
    candidate = {
        'type': 'object', 'additionalProperties': False,
        'properties': {
            'candidate_id': {'type': 'string', 'pattern': '^EU-CAND-[0-9]{4,}$'},
            'title': {'type': 'string', 'minLength': 1},
            'evidence_status': {'enum': ['context-only', 'local-mention-only', 'source-inspected', 'proposed']},
            'development_status': {'enum': ['partially-developed-reported', 'scope-only', 'existing-software-needs-teaching-adaptation', 'proposed-future-component']},
            'functions': props['functions'], 'domains': props['domains'],
            'proposed_content_type': props['content_type'], 'proposed_pathways': props['pathways'],
            'proposed_difficulty': props['difficulty'],
            'potential_outputs': {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}},
            'sources': {'type': 'array', 'minItems': 1, 'items': {'type': 'string', 'minLength': 1}},
            'limitations': {'type': 'string', 'minLength': 1}, 'catalogue_ready': {'const': False},
        },
    }
    candidate['required'] = list(candidate['properties'])
    schema = {'type': 'object', 'additionalProperties': False, 'properties': {
        'schema_version': {'const': '0.1.0'}, 'inventory_date': {'type': 'string', 'format': 'date'},
        'status': {'const': 'review-draft'}, 'classification_note': {'type': 'string', 'minLength': 1},
        'candidates': {'type': 'array', 'items': candidate},
    }, 'required': ['schema_version', 'inventory_date', 'status', 'classification_note', 'candidates']}
    check_schema(data, schema)
    ids = [c['candidate_id'] for c in data['candidates']]
    if len(ids) != len(set(ids)):
        raise ValidationError('Duplicate candidate ID')


def check_links(root):
    for path in root.rglob('*.md'):
        for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)', path.read_text()):
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            contained(root, str(path.parent.relative_to(root) / unquote(url.path)))


def check_domain(data):
    check_schema(data, {'type': 'object', 'additionalProperties': False, 'properties': {
        'domain_id': {'enum': DOMAINS}, 'title': {'type': 'string', 'pattern': r'\S'},
        'page_kind': {'const': 'domain'}, 'status': {'const': 'foundational-draft'},
        'taxonomy_version': {'const': '0.1.0'},
        'card_summary': {'type': 'string', 'pattern': r'\S'},
        'subject_classification': {'enum': list(SUBJECTS)},
        'approach': {'enum': list(APPROACHES)},
    }, 'required': ['domain_id', 'title', 'page_kind', 'status', 'taxonomy_version',
                    'card_summary', 'subject_classification', 'approach']})
    summary = data['card_summary'].strip()
    if re.match(r'This domain\b', summary, re.I):
        raise ValidationError('Card summary must not begin with "This domain"')
    sentences = [part for part in re.split(r'[.!?]+(?:\s+|$)', summary) if part.strip()]
    if len(sentences) > 2:
        raise ValidationError('Card summary must contain no more than two sentences')


def validate_source(root):
    root = Path(root).resolve()
    schema = json.loads((root / 'architecture/metadata.schema.json').read_text())
    domain_paths = sorted((root / 'domains').glob('*.md'))
    seen = []
    for path in domain_paths:
        data = frontmatter(path)
        check_domain(data)
        if not path.name.startswith(data['domain_id'] + '-'):
            raise ValidationError('Domain filename and ID disagree')
        seen.append(data['domain_id'])
    if sorted(seen) != DOMAINS:
        raise ValidationError('Expected exactly one page for each EU-01–EU-10 domain')
    check_inventory(parse_yaml((root / 'inventory/courseware-candidates.yaml').read_text()), schema)
    check_record(frontmatter(root / 'architecture/component-template.md'), root, schema, example=True)
    check_record(parse_yaml((root / 'architecture/programme-example.yaml').read_text()), root, schema, example=True)
    records = []
    for folder in ('components', 'programmes'):
        for path in sorted((root / folder).rglob('*.md')):
            contained(root, str(path.relative_to(root)))
            data = frontmatter(path)
            check_record(data, root, schema)
            records.append(data)
    check_graph(records)
    check_links(root)
    return domain_paths, records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    args = parser.parse_args()
    domains, records = validate_source(args.source)
    print(f'Validated {len(domains)} domains, inventory, two synthetic examples, links and {len(records)} authored resources.')
