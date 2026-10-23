"""Publish approved GISDS research and website-only navigation from committed bytes."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File
from scripts.publication_diagrams import diagram_markup

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/GISDS"
CATALOGUE = "information/GISDS/index.md"
GUIDE = "information/GISDS/research-guide.md"
EXPECTED = {"GISDS.md": CATALOGUE, "README.md": GUIDE}
ASSETS = {"assets/diagrams/gisds_overview.svg": "information/GISDS/assets/diagrams/gisds_overview.svg"}
OVERVIEW_NAV = "\n\n---\n\n[Browse the GISDS catalogue and research guide](GISDS/index.md)\n"


def manifest():
    data = json.loads((ROOT / "publications/gisds.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", "")):
        raise ConfigurationError("GISDS requires the approved repository and full commit SHA.")
    entries = data.get("documents", [])
    assets = data.get("assets", [])
    if len(assets) != 1 or {d["source"]: d["page"] for d in assets} != ASSETS or len(entries) != 2 or {d["source"]: d["page"] for d in entries} != EXPECTED or any(
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
    if any(f.src_uri in {*EXPECTED.values(), *ASSETS.values()} for f in files):
        raise ConfigurationError("GISDS publication destination already exists.")
    for item in data["documents"]:
        content = read_document(source, data["commit"], item)
        files.append(File.generated(config, item["page"], content=content))
    # Copy verified committed SVG bytes; never execute the source renderer.
    for item in data["assets"]:
        files.append(File.generated(config, item["page"], content=read_file(source, data["commit"], item)))
    return files


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        # Website navigation only: do not edit or duplicate the umbrella manuscript.
        return markdown + OVERVIEW_NAV
    if page.file.src_uri == CATALOGUE:
        # The complete source table follows verbatim, without rewriting any cell.
        data = manifest()
        source = Path(os.environ.get("GISDS_SOURCE", str(ROOT.parent / "ecological-information/GISDS"))).expanduser()
        guide = next(item for item in data["documents"] if item["source"] == "README.md")
        diagram = diagram_markup(read_document(source, data["commit"], guide), next(iter(ASSETS)))
        return "# GISDS — Resource catalogue\n\n" + diagram + "\n\n[Research guide, academic attribution and reuse guidance](research-guide.md)\n\n" + markdown
    if page.file.src_uri == GUIDE:
        data = manifest()
        markdown = markdown.replace("](GISDS.md)", "](index.md)")
        for name in ["CITATION.cff", "CHANGELOG.md"]:
            markdown = markdown.replace(f"]({name})", f"]({data['repository']}/blob/{data['commit']}/{name})")
        return markdown
    return markdown
