"""Publish approved GISDS research and website-only navigation from committed bytes."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File
ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/GISDS"
CATALOGUE = "information/GISDS/resource-catalogue.md"
GUIDE = "information/GISDS/index.md"
NOTES = "information/GISDS/research-notes.md"
LEGACY_GUIDE = "information/GISDS/research-guide.md"
EXPECTED = {"GISDS.md": CATALOGUE, "README.md": GUIDE, "RESEARCH_NOTES.md": NOTES}
ASSETS = {"assets/diagrams/gisds_overview.svg": "information/GISDS/assets/diagrams/gisds_overview.svg"}
OVERVIEW_NAV = "\n\n---\n\n[Browse the GISDS catalogue and research guide](GISDS/index.md)\n"


def manifest():
    data = json.loads((ROOT / "publications/gisds.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", "")):
        raise ConfigurationError("GISDS requires the approved repository and full commit SHA.")
    entries = data.get("documents", [])
    assets = data.get("assets", [])
    if len(assets) != 1 or {d["source"]: d["page"] for d in assets} != ASSETS or len(entries) != 3 or {d["source"]: d["page"] for d in entries} != EXPECTED or any(
        not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in entries + assets
    ):
        raise ConfigurationError("Unexpected GISDS document allowlist or checksum.")
    return data


def read_file(source, commit, item):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show", f"{commit}:{item['source']}"],
        capture_output=True,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item["sha256"]:
        raise ConfigurationError("GISDS source unavailable or checksum mismatch; check GISDS_SOURCE.")
    return result.stdout


def read_document(source, commit, item):
    return read_file(source, commit, item).decode("utf-8")


def on_files(files, config):
    data = manifest()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and not os.environ.get("GISDS_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require GISDS_SOURCE.")
    source = Path(os.environ.get("GISDS_SOURCE", str(ROOT.parent / "ecological-information/GISDS"))).expanduser()
    if any(f.src_uri in {*EXPECTED.values(), LEGACY_GUIDE, *ASSETS.values()} for f in files):
        raise ConfigurationError("GISDS publication destination already exists.")
    for item in data["documents"]:
        content = read_document(source, data["commit"], item)
        files.append(File.generated(config, item["page"], content=content))
    # Preserve the old guide route and its heading fragments from pinned notes.
    notes = next(item for item in data["documents"] if item["source"] == "RESEARCH_NOTES.md")
    files.append(File.generated(config, LEGACY_GUIDE, content=read_document(source, data["commit"], notes)))
    # Copy verified committed SVG bytes; never execute the source renderer.
    for item in data["assets"]:
        files.append(File.generated(config, item["page"], content=read_file(source, data["commit"], item)))
    return files


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        # Website navigation only: do not edit or duplicate the umbrella manuscript.
        return markdown + OVERVIEW_NAV
    if page.file.src_uri == CATALOGUE:
        # Keep every source table cell unchanged; the diagram belongs only to GUIDE.
        return "# GISDS — Resource Catalogue\n\n[Geographic Sources Overview and research guide](index.md)\n\n" + markdown
    if page.file.src_uri in {GUIDE, NOTES, LEGACY_GUIDE}:
        data = manifest()
        for source_name, target in {"GISDS.md": "resource-catalogue.md", "README.md": "index.md", "RESEARCH_NOTES.md": "research-notes.md"}.items():
            markdown = markdown.replace(f"]({source_name})", f"]({target})")
        for name in ["CITATION.cff", "CHANGELOG.md"]:
            markdown = markdown.replace(f"]({name})", f"]({data['repository']}/blob/{data['commit']}/{name})")
        if page.file.src_uri == GUIDE:
            # Retain the former catalogue heading and catalogue-link fragments.
            markdown = markdown.replace("## Resource Catalogue\n", '<a id="gisds-resource-catalogue"></a>\n<a id="catalogue"></a>\n\n## Resource Catalogue\n')
        else:
            markdown = markdown.replace('\n\n', '\n\n<a id="gisds"></a>\n<a id="gisds-geographic-sources-overview"></a>\n\n[The concise Overview is the Geographic Sources landing page.](index.md)\n\n', 1)
        return markdown
    return markdown
