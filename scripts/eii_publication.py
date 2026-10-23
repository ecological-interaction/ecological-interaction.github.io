"""Publish pinned EII reading pages and access to authoritative source references."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File
# MkDocs loads hooks by file path; resolve the helper independently of sys.path.
_diagram_spec = importlib.util.spec_from_file_location(
    "publication_diagrams", Path(__file__).with_name("publication_diagrams.py")
)
if _diagram_spec is None or _diagram_spec.loader is None:
    raise ConfigurationError("Cannot load the adjacent publication diagram helper.")
_diagram_module = importlib.util.module_from_spec(_diagram_spec)
_diagram_spec.loader.exec_module(_diagram_module)
diagram_markup = _diagram_module.diagram_markup

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/EII"
CATALOGUE = "information/EII/index.md"
GUIDE = "information/EII/research-guide.md"
MACHINE = "information/EII/machine-reference.md"
EXPECTED = {"EII_Scientific_Reference_Register.md": CATALOGUE, "README.md": GUIDE}
REFERENCES = {"EII_Machine_Reference.md", "EII - Remote Sensing.md"}
ASSETS = {"assets/diagrams/eii_overview.svg": "information/EII/assets/diagrams/eii_overview.svg"}
OVERVIEW_NAV = "\n\n[Browse the EII scientific catalogue and research guide](EII/index.md)\n"


def manifest():
    data = json.loads((ROOT / "publications/eii.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", "")):
        raise ConfigurationError("EII requires the approved repository and full commit SHA.")
    documents = data.get("documents", [])
    references = data.get("references", [])
    assets = data.get("assets", [])
    if (len(documents) != 2 or {d["source"]: d["page"] for d in documents} != EXPECTED
            or len(references) != 2 or {d["source"] for d in references} != REFERENCES
            or len(assets) != 1 or {d["source"]: d["page"] for d in assets} != ASSETS
            or any(not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in documents + references + assets)):
        raise ConfigurationError("Unexpected EII source allowlist or checksum.")
    return data


def read_file(source, commit, item):
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
        return f"https://raw.githubusercontent.com/ecological-interaction/EII/{data['commit']}/{quote(name)}"
    return f"{data['repository']}/blob/{data['commit']}/{quote(name)}"


def machine_access(data):
    machine = "EII_Machine_Reference.md"
    subset = "EII - Remote Sensing.md"
    checksum = next(r["sha256"] for r in data["references"] if r["source"] == machine)
    return (
        "# EII — Authoritative machine reference\n\n"
        "**Work in Progress — Academic Research Resource**\n\n"
        "Jonathan Minchin · Ecological Interaction · "
        "[ORCID 0000-0001-8152-1796](https://orcid.org/0000-0001-8152-1796).\n\n"
        "The machine reference is the authoritative complete scientific record. "
        "The [Scientific Reference Register](index.md) is its human-readable academic "
        "presentation; see the [research guide](research-guide.md) for scope, "
        "versions and outstanding editorial decisions.\n\n"
        f"- [View the authoritative machine-reference source]({source_url(data, machine)}).\n"
        f"- [Open the raw Markdown file]({source_url(data, machine, raw=True)}).\n"
        f"- [View the 91-record remote-sensing subset]({source_url(data, subset)}).\n\n"
        "The machine source contains a manifest, 235 indicator objects and historical "
        "context in 237 fenced JSON blocks. It is Markdown containing JSON blocks, "
        "not a standalone JSON file. Historical source material is preserved as "
        "documented in that file. No research content is independently maintained "
        "on this access page.\n\n"
        f"Approved source commit: `{data['commit']}`.\n\n"
        f"Machine-reference SHA-256: `{checksum}`.\n\n"
        "Public access and citation metadata do not grant reuse permission. "
        "No repository licence has been selected; third-party works and datasets "
        "retain their own conditions. This site does not host observation datasets.\n"
    )


def on_files(files, config):
    data = manifest()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and not os.environ.get("EII_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require EII_SOURCE.")
    source = Path(os.environ.get("EII_SOURCE", str(ROOT.parent / "ecological-information/EII"))).expanduser()
    if any(f.src_uri in {*EXPECTED.values(), *ASSETS.values(), MACHINE} for f in files):
        raise ConfigurationError("EII publication destination already exists.")
    # Verify linked references too, but do not import their large research bodies.
    for item in data["references"]:
        read_document(source, data["commit"], item)
    for item in data["documents"]:
        files.append(File.generated(config, item["page"], content=read_document(source, data["commit"], item)))
    # Copy verified committed SVG bytes; never execute the source renderer.
    for item in data["assets"]:
        files.append(File.generated(config, item["page"], content=read_file(source, data["commit"], item)))
    files.append(File.generated(config, MACHINE, content=machine_access(data)))
    return files


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        return markdown + OVERVIEW_NAV
    if page.file.src_uri not in {CATALOGUE, GUIDE}:
        return markdown
    data = manifest()
    # Presentation-only link mapping; all academic text and table cells stay intact.
    for name, target in {
        "EII_Scientific_Reference_Register.md": "index.md",
        "EII_Machine_Reference.md": "machine-reference.md",
        "EII%20-%20Remote%20Sensing.md": source_url(data, "EII - Remote Sensing.md"),
        "CITATION.cff": source_url(data, "CITATION.cff"),
        "CHANGELOG.md": source_url(data, "CHANGELOG.md"),
    }.items():
        markdown = markdown.replace(f"]({name})", f"]({target})")
    if page.file.src_uri == CATALOGUE:
        source = Path(os.environ.get("EII_SOURCE", str(ROOT.parent / "ecological-information/EII"))).expanduser()
        guide = next(item for item in data["documents"] if item["source"] == "README.md")
        diagram = diagram_markup(read_document(source, data["commit"], guide), next(iter(ASSETS)))
        if markdown.startswith("# "):
            title, newline, body = markdown.partition("\n")
            markdown = title + "\n\n" + diagram + "\n" + body
        else:
            markdown = diagram + "\n\n" + markdown
        markdown = "[Research guide](research-guide.md) · [Authoritative machine reference](machine-reference.md)\n\n" + markdown
    return markdown
