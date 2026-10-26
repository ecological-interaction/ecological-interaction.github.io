"""Publish checksum-pinned EIRKB reading views and verbatim downloadable records."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/EIRKB"
MARKER = "<!-- EIRKB_PREVIEW_LINK -->"
BASE = "information/EIRKB/"
INTRODUCTION = BASE + "index.md"
REGISTER = BASE + "scientific-reference-register.md"
LEGACY_REGISTER = BASE + "reference-register.md"
HISTORY = BASE + "history-and-theory.md"
MACHINE = BASE + "machine-reference.md"
WORKBOOK = "registers/ecological_information_complete_reference_register_v0.1.xlsx"
EXPECTED = {
    "README.md": INTRODUCTION,
    "EIRKB_Scientific_Reference_Register.md": REGISTER,
    "EIRKB_Research_Protocol.md": BASE + "research-protocol.md",
    "A01_Historic_Arc.md": BASE + "historic-arc.md",
    "A02_Intellectual_Lineages.md": BASE + "intellectual-lineages.md",
    "A03_Intellectual_Map.md": BASE + "intellectual-map.md",
    "MASTER_history_theory_ecological_information.md": HISTORY,
    "CHANGELOG.md": BASE + "changelog.md",
}
ASSETS = {name: BASE + name for name in (
    "assets/diagrams/eirkb_federation.svg", "assets/diagrams/eirkb_overview.svg",
    "EIRKB_Machine_Reference.json", "EIRKB_Machine_Reference.schema.json",
    "EIRKB_Preservation_Crosswalk.json", "CITATION.cff",
)}
REFERENCES = {
    "assets/diagrams/eirkb_federation.mmd", "assets/diagrams/render_eirkb_federation.py",
    "assets/diagrams/eirkb_overview.mmd", "assets/diagrams/render_eirkb_overview.py",
}
WORKBOOK_NAMES = {
    "ecological_information_complete_reference_register_V0.xlsx",
    "ecological_information_complete_reference_register_v0.1.xlsx",
}
_manifest = None


def read_file(source, commit, document):
    """Read committed bytes; a missing object or checksum mismatch rejects the build."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ConfigurationError("EIRKB publication requires a full commit SHA.")
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show", f"{commit}:{document['source']}"],
        capture_output=True,
    )
    if result.returncode:
        raise ConfigurationError("The selected EIRKB commit/document is unavailable. Check EIRKB_SOURCE.")
    if hashlib.sha256(result.stdout).hexdigest() != document["sha256"]:
        raise ConfigurationError("EIRKB document checksum differs from the approved manifest.")
    return result.stdout


def read_document(source, commit, document):
    return read_file(source, commit, document).decode("utf-8")


def manifest(data=None):
    if data is None:
        data = json.loads((ROOT / "publications/eirkb.json").read_text())
    documents, references, assets = (data.get(key, []) for key in ["documents", "references", "assets"])
    if (data.get("repository") != REPOSITORY
            or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", ""))
            or len(documents) != len(EXPECTED) or {d["source"]: d["page"] for d in documents} != EXPECTED
            or len(references) != len(REFERENCES) or {d["source"] for d in references} != REFERENCES
            or len(assets) != len(ASSETS) or {d["source"]: d["page"] for d in assets} != ASSETS
            or any(not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in documents + references + assets)):
        raise ConfigurationError("Unexpected EIRKB repository, commit, allowlist or checksum.")
    return data


def source_checkout():
    return Path(os.environ.get("EIRKB_SOURCE", str(ROOT.parent / "ecological-information/EIRKB"))).expanduser()


def on_config(config):
    global _manifest
    _manifest = None
    hosted = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    preview = os.environ.get("EIRKB_PREVIEW") == "1"
    if preview and hosted:
        raise ConfigurationError("EIRKB_PREVIEW is local-only; hosted builds must use the normal site output.")
    if hosted and not os.environ.get("EIRKB_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require the approved EIRKB checkout at EIRKB_SOURCE.")
    _manifest = manifest()
    if preview:
        config.site_dir = str(ROOT / "site-preview")
    return config


def machine_access():
    return (
        "# EIRKB — Machine Reference\n\n"
        "The structured reference records are available as JSON. The "
        "[Scientific Reference Register](scientific-reference-register.md) presents the research tables; "
        "the [Research Protocol](research-protocol.md) explains their authority and provenance.\n\n"
        '<a href="../EIRKB_Machine_Reference.json" download="EIRKB_Machine_Reference.json">Download the Machine Reference (JSON)</a>\n\n'
        "[Citation metadata](CITATION.cff).\n"
    )


def on_files(files, config):
    data = manifest(_manifest)
    source = source_checkout()
    destinations = {*EXPECTED.values(), *ASSETS.values(), LEGACY_REGISTER, MACHINE}
    if any(f.src_uri in destinations for f in files):
        raise ConfigurationError("EIRKB publication destination already exists.")
    # Verify the corresponding editable diagram sources/renderers, but never execute them.
    for item in data["references"]:
        read_file(source, data["commit"], item)
    contents = {}
    for item in data["documents"]:
        text = read_document(source, data["commit"], item)
        contents[item["source"]] = text
        files.append(File.generated(config, item["page"], content=text))
    for item in data["assets"]:
        content = read_file(source, data["commit"], item)
        if item["source"].endswith(".json"):
            try:
                json.loads(content)
            except (ValueError, UnicodeDecodeError) as exc:
                raise ConfigurationError("Pinned EIRKB JSON asset is invalid.") from exc
        files.append(File.generated(config, item["page"], content=content))
    files.append(File.generated(config, LEGACY_REGISTER, content=contents["EIRKB_Scientific_Reference_Register.md"]))
    files.append(File.generated(config, MACHINE, content=machine_access()))
    return files


def source_url(data, name):
    return f"{data['repository']}/blob/{data['commit']}/{quote(name, safe='/')}"


def map_links(markdown, data):
    # Map working links only. Code/provenance strings and every scientific cell value remain source-owned.
    destinations = {name: page.removeprefix(BASE) for name, page in {**EXPECTED, **ASSETS}.items()}
    destinations["EIRKB Reference Register.md"] = REGISTER.removeprefix(BASE)
    def replace(match):
        target = match[1]
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            return match[0]
        name = unquote(url.path)
        mapped = destinations.get(name)
        if mapped is None and name in REFERENCES:
            mapped = source_url(data, name)
        if mapped is None and name.startswith(("registers/", "_legacy registers/")):
            filename = name.split("/", 1)[1]
            if filename in WORKBOOK_NAMES:
                mapped = source_url(data, "_legacy registers/" + filename)
        if mapped is None:
            return match[0]
        if url.query:
            mapped += "?" + url.query
        if url.fragment:
            mapped += "#" + url.fragment
        return "](" + mapped + ")"
    return re.sub(r"\]\(([^\s)]+)\)", replace, markdown)


def history_links(data):
    item = next(a for a in data["assets"] if a["source"] == "EIRKB_Preservation_Crosswalk.json")
    crosswalk = json.loads(read_file(source_checkout(), data["commit"], item))
    headings = crosswalk["master_headings_and_anchors"]
    mapping = {h["anchor"]: (h["destination"], h["original_heading"].lstrip("# ")) for h in headings}
    for item in crosswalk["master_explicit_anchors"]:
        mapping[item["anchor"]] = (item["destination"], item["anchor"])
    lines = ["\n\n## Historical section links\n\n",
             "Existing bookmarks are retained below. Follow the corresponding link to read the section in its analytical document.\n\n",
             "| Original section | Current reading location |\n|---|---|\n"]
    for anchor, (destination, label) in mapping.items():
        page = EXPECTED[destination].removeprefix(BASE)
        alias = "" if anchor == "history-and-theory-of-ecological-information" else f'<a id="{anchor}"></a>'
        label = label.replace("|", "&#124;")
        lines.append(f"| {alias}{label} | [Read section]({page}#{anchor}) |\n")
    return "".join(lines)


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        return markdown.replace(MARKER, "[EIRKB — Ecological Information Research Knowledge Base](EIRKB/index.md)")
    if page.file.src_uri not in {*EXPECTED.values(), LEGACY_REGISTER, MACHINE}:
        return markdown
    data = manifest(_manifest)
    markdown = map_links(markdown, data)
    if page.file.src_uri == INTRODUCTION:
        markdown += '\n\n<a id="ecological-information-reference-knowledge-base"></a>\n<a id="read-the-research"></a>\n'
    if page.file.src_uri in {REGISTER, LEGACY_REGISTER}:
        markdown += (
            '\n\n<a id="eirkb-reference-register"></a>\n<a id="contents"></a>\n\n## Historical register sections\n\n'
            '<a id="guide"></a>\n\n[Historical Guide and research protocol](research-protocol.md#guide).\n\n'
            '<a id="migration"></a>\n\n[Migration provenance appendix](changelog.md#migration).\n'
        )
    elif page.file.src_uri == HISTORY:
        markdown += history_links(data)
    return markdown
