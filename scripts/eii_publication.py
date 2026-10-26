"""Publish checksum-pinned EII reading views; scientific authorities stay on GitHub."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit

from markdown import markdown as render_markdown
from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/EII"
CATALOGUE = "information/EII/index.md"
GUIDE = "information/EII/research-guide.md"
MACHINE = "information/EII/machine-reference.md"
REMOTE = "information/EII/remote-sensing.md"
OBSERVATIONAL = "information/EII/observational-systems.md"
EXPECTED = {'README.md': 'information/EII/index.md', 'EII - Remote Sensing.md': 'information/EII/remote-sensing.md', 'EII_Observational_Systems.md': 'information/EII/observational-systems.md'}
REFERENCES = {'EII_Preservation_Crosswalk.json', 'EII_Machine_Reference.md', 'EII_Machine_Reference.schema.json', 'EII_Scientific_Reference_Register.md', 'assets/diagrams/eii_overview.mmd', 'assets/diagrams/render_eii_overview.py', 'EII_Machine_Reference.json', 'CITATION.cff', 'CHANGELOG.md', 'EII_Research_Protocol.md'}
ASSETS = {'assets/diagrams/eii_overview.svg': 'information/EII/assets/diagrams/eii_overview.svg'}
LEGACY_LANDING_ANCHORS = ('eii-ecological-indicator-inventory', '1-purpose-and-boundaries', 'reading-key', 'domain-index', '2-consolidated-indicator-register-stage-a', 'd01', 'd01-atmosphere-and-climate', 'd02', 'd02-hydrology', 'd03', 'd03-soil-physics', 'd04', 'd04-soil-chemistry', 'd05', 'd05-soil-biology', 'd06', 'd06-biodiversity', 'd07', 'd07-vegetation', 'd08', 'd08-ecological-interactions', 'd09', 'd09-biogeochemical-cycles', 'd10', 'd10-landscape-ecology', 'd11', 'd11-ecosystem-functioning', 'd12', 'd12-ecological-resilience', 'd13', 'd13-agricultural-ecology', 'd14', 'd14-humanecological-systems', 'd15', 'd15-planetary-and-regional-boundaries', '3-observation-platforms-and-information-products', '4-trails4soil-regenerative-practices-exploratory-indicator-crosswalk', '5-cross-domain-questions-and-example-indicator-combinations', '6-proposed-record-schema-for-later-interoperability', '7-source-and-verification-register-starter', '8-editorial-rules-and-roadmap', 'known-gaps-for-subsequent-stage-a-expansions', 'version-history', '9-scientific-domain-classification-consolidated-edition', '10-scientific-references-consolidated-edition', 'consolidated-edition-history')
LEGACY_GUIDE_ANCHORS = ('eii-ecological-indicator-inventory', 'start-here', 'maintaining-the-files', 'domain-taxonomy-and-document-versions', 'repository-and-publication-status', 'register-comparison-and-publication-review', 'database-reference-methodology-alignment', 'historical-scope-review-trails4soil', 'historical-provenance-requiring-research-review', 'proposed-academic-reading-interface')
OVERVIEW_NAV = "\n\n[Browse the EII scientific catalogue and research guide](EII/index.md)\n"


def manifest():
    data = json.loads((ROOT / "publications/eii.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", "")):
        raise ConfigurationError("EII requires the approved repository and full commit SHA.")
    documents, references, assets = (data.get(key, []) for key in ["documents", "references", "assets"])
    if (len(documents) != len(EXPECTED) or {d["source"]: d["page"] for d in documents} != EXPECTED
            or len(references) != len(REFERENCES) or {d["source"] for d in references} != REFERENCES
            or len(assets) != len(ASSETS) or {d["source"]: d["page"] for d in assets} != ASSETS
            or any(not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in documents + references + assets)):
        raise ConfigurationError("Unexpected EII source allowlist or checksum.")
    return data


def source_checkout():
    return Path(os.environ.get("EII_SOURCE", str(ROOT.parent / "ecological-information/EII"))).expanduser()


def read_file(source, commit, item):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ConfigurationError("EII requires an explicitly approved full commit SHA.")
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show", f"{commit}:{item['source']}"],
        capture_output=True,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item["sha256"]:
        raise ConfigurationError("EII source unavailable or checksum mismatch; check EII_SOURCE.")
    return result.stdout


def read_document(source, commit, item):
    return read_file(source, commit, item).decode("utf-8")


def source_url(data, name, raw=False):
    if raw:
        return f"https://raw.githubusercontent.com/ecological-interaction/EII/{data['commit']}/{quote(name, safe='/')}"
    return f"{data['repository']}/blob/{data['commit']}/{quote(name, safe='/')}"


def machine_access(data):
    return (
        "# EII — Authoritative machine reference\n\n"
        "The authoritative structured records are now a single JSON document. "
        f"[View the Machine Reference JSON]({source_url(data, 'EII_Machine_Reference.json')}) "
        f"or [open the raw JSON]({source_url(data, 'EII_Machine_Reference.json', raw=True)}). "
        f"The [Scientific Register]({source_url(data, 'EII_Scientific_Reference_Register.md')}) "
        f"provides the human-readable research; the [Research Protocol]({source_url(data, 'EII_Research_Protocol.md')}) "
        "explains methods and governance.\n\n"
        "[Return to EII](index.md).\n\n"
        "Jonathan Minchin · Ecological Interaction · "
        "[ORCID 0000-0001-8152-1796](https://orcid.org/0000-0001-8152-1796). "
        f"[Citation metadata]({source_url(data, 'CITATION.cff')}).\n"
    )


def guide_access(data):
    text = (
        "# EII — Research Guide\n\n"
        "The research guide is now the [EII — Ecological Indicator Inventory landing page](index.md). "
        f"Detailed methods and governance are available in the [Research Protocol]({source_url(data, 'EII_Research_Protocol.md')}).\n"
    )
    return text + compatibility_anchors(text, LEGACY_GUIDE_ANCHORS)


def on_files(files, config):
    data = manifest()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and not os.environ.get("EII_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require EII_SOURCE.")
    source = source_checkout()
    if any(f.src_uri in {*EXPECTED.values(), *ASSETS.values(), MACHINE, GUIDE} for f in files):
        raise ConfigurationError("EII publication destination already exists.")
    # Source-only authorities and editable diagram files are verified, never rendered/executed.
    for item in data["references"]:
        content = read_file(source, data["commit"], item)
        if item["source"].endswith(".json"):
            try:
                json.loads(content)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ConfigurationError("Pinned EII JSON reference is invalid.") from exc
    for item in data["documents"]:
        files.append(File.generated(config, item["page"], content=read_document(source, data["commit"], item)))
    for item in data["assets"]:
        files.append(File.generated(config, item["page"], content=read_file(source, data["commit"], item)))
    files.append(File.generated(config, GUIDE, content=guide_access(data)))
    files.append(File.generated(config, MACHINE, content=machine_access(data)))
    return files


def compatibility_anchors(text, original):
    rendered = render_markdown(text, extensions=["toc", "tables", "fenced_code"])
    existing = set(re.findall(r'\bid="([^\"]+)"', rendered))
    return "\n\n" + "".join(f'<a id="{anchor}"></a>\n' for anchor in original if anchor not in existing)


def map_links(text, data):
    local = {name: page.removeprefix("information/EII/") for name, page in {**EXPECTED, **ASSETS}.items()}
    def replace(match):
        target = match[1]
        angle = target.startswith("<") and target.endswith(">")
        url = urlsplit(target[1:-1] if angle else target)
        name = unquote(url.path)
        if url.scheme or url.netloc:
            prefix = "/ecological-interaction/EII/blob/main/"
            if url.scheme != "https" or url.netloc != "github.com" or not name.startswith(prefix):
                return match[0]
            name = name.removeprefix(prefix)
            # Supporting README links remain on GitHub at the immutable publication revision.
            if name not in REFERENCES:
                return match[0]
            mapped = source_url(data, name)
        elif not name:
            return match[0]
        elif name in local:
            mapped = local[name]
        elif name in REFERENCES:
            if name == "EII_Machine_Reference.md" and url.fragment:
                name = "EII_Scientific_Reference_Register.md"
            mapped = source_url(data, name)
        else:
            return match[0]
        if url.query:
            mapped += "?" + url.query
        if url.fragment:
            mapped += "#" + url.fragment
        return "](" + ("<" + mapped + ">" if angle else mapped) + ")"
    # Working Markdown links only: preserve fenced code and inline-code provenance byte-for-byte.
    lines = []; fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r"^[ \t]{0,3}(`{3,}|~{3,})", line)
        if marker:
            value = marker[1]
            if fence is None: fence = (value[0], len(value))
            elif value[0] == fence[0] and len(value) >= fence[1]: fence = None
            lines.append(line); continue
        if fence or line.startswith(("    ", "\t")):
            lines.append(line); continue
        pieces = re.split(r"(`+[^`\n]*`+)", line)
        lines.append("".join(piece if piece.startswith("`") else re.sub(r"\]\(([^)\n]+)\)", replace, piece) for piece in pieces))
    return "".join(lines)


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        return markdown + OVERVIEW_NAV
    if page.file.src_uri not in EXPECTED.values():
        return markdown
    data = manifest()
    markdown = map_links(markdown, data)
    if page.file.src_uri == CATALOGUE:
        markdown += compatibility_anchors(markdown, LEGACY_LANDING_ANCHORS)
    return markdown
