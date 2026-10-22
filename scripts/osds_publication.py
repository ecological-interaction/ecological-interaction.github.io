"""Publish pinned OSDS reading pages and access to authoritative source references."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/OSDS"
CATALOGUE = "information/OSDS/index.md"
GUIDE = "information/OSDS/research-guide.md"
MACHINE = "information/OSDS/machine-reference.md"
EXPECTED = {"OSDS_Scientific_Reference_Register.md": CATALOGUE, "README.md": GUIDE}
REFERENCES = {"OSDS_Machine_Reference.md"}
ASSETS = {"assets/diagrams/osds_federation.svg": "information/OSDS/assets/diagrams/osds_federation.svg"}
OVERVIEW_NAV = "\n\n[Browse the OSDS scientific catalogue and research guide](OSDS/index.md)\n"


def manifest():
    data = json.loads((ROOT / "publications/osds.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", "")):
        raise ConfigurationError("OSDS requires the approved repository and full commit SHA.")
    documents = data.get("documents", [])
    references = data.get("references", [])
    assets = data.get("assets", [])
    if (len(documents) != 2 or {d["source"]: d["page"] for d in documents} != EXPECTED
            or len(references) != 1 or {d["source"] for d in references} != REFERENCES
            or len(assets) != len(ASSETS) or {a["source"]: a["page"] for a in assets} != ASSETS
            or any(not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in documents + references + assets)):
        raise ConfigurationError("Unexpected OSDS source allowlist or checksum.")
    return data


def read_file(source, commit, item):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show", f"{commit}:{item['source']}"],
        capture_output=True,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item["sha256"]:
        raise ConfigurationError("OSDS source unavailable or checksum mismatch; check OSDS_SOURCE.")
    return result.stdout


def read_document(source, commit, item):
    return read_file(source, commit, item).decode("utf-8")


def source_url(data, name, raw=False):
    if raw:
        return f"https://raw.githubusercontent.com/ecological-interaction/OSDS/{data['commit']}/{quote(name)}"
    return f"{data['repository']}/blob/{data['commit']}/{quote(name)}"


def machine_access(data):
    machine = "OSDS_Machine_Reference.md"
    checksum = next(r["sha256"] for r in data["references"] if r["source"] == machine)
    return (
        "# OSDS — Authoritative machine reference\n\n"
        "**Work in Progress — Academic Research Resource**\n\n"
        "Jonathan Minchin · Ecological Interaction · "
        "[ORCID 0000-0001-8152-1796](https://orcid.org/0000-0001-8152-1796).\n\n"
        "The machine reference is the authoritative complete scientific record. "
        "The [Scientific Reference Register](index.md) is its human-readable academic "
        "presentation; see the [research guide](research-guide.md) for scope, "
        "versions and outstanding editorial decisions.\n\n"
        f"- [View the authoritative machine-reference source]({source_url(data, machine)}).\n"
        f"- [Open the raw Markdown file]({source_url(data, machine, raw=True)}).\n\n"
        "The machine source contains a manifest and 62 candidate source records with "
        "provenance in 63 fenced JSON blocks. It is Markdown containing JSON blocks, "
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
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and not os.environ.get("OSDS_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require OSDS_SOURCE.")
    source = Path(os.environ.get("OSDS_SOURCE", str(ROOT.parent / "ecological-information/OSDS"))).expanduser()
    if any(f.src_uri in {*EXPECTED.values(), *ASSETS.values(), MACHINE} for f in files):
        raise ConfigurationError("OSDS publication destination already exists.")
    # Verify linked references too, but do not import their large research bodies.
    for item in data["references"]:
        read_document(source, data["commit"], item)
    for item in data["documents"]:
        files.append(File.generated(config, item["page"], content=read_document(source, data["commit"], item)))
    # Import the approved bytes only; never execute the source diagram renderer.
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
        "OSDS_Scientific_Reference_Register.md": "index.md",
        "OSDS_Machine_Reference.md": "machine-reference.md",
        "CITATION.cff": source_url(data, "CITATION.cff"),
        "CHANGELOG.md": source_url(data, "CHANGELOG.md"),
    }.items():
        markdown = markdown.replace(f"]({name})", f"]({target})")
    # Keep record fragments on the authoritative pinned source, not on the access page.
    markdown = re.sub(
        r"\]\(OSDS_Machine_Reference\.md#(src-[0-9]{3})\)",
        lambda match: f"]({source_url(data, 'OSDS_Machine_Reference.md')}#{match.group(1)})",
        markdown,
    )
    if page.file.src_uri == CATALOGUE:
        markdown = "[Research guide](research-guide.md) · [Authoritative machine reference](machine-reference.md)\n\n" + markdown
    return markdown
