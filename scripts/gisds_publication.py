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
CATALOGUE = "information/GISDS/index.md"
GUIDE = "information/GISDS/research-guide.md"
EXPECTED = {"GISDS.md": CATALOGUE, "README.md": GUIDE}
OVERVIEW_NAV = "\n\n---\n\n[Browse the GISDS catalogue and research guide](GISDS/index.md)\n"


def manifest():
    data = json.loads((ROOT / "publications/gisds.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", "")):
        raise ConfigurationError("GISDS requires the approved repository and full commit SHA.")
    entries = data.get("documents", [])
    if len(entries) != 2 or {d["source"]: d["page"] for d in entries} != EXPECTED or any(
        not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in entries
    ):
        raise ConfigurationError("Unexpected GISDS document allowlist or checksum.")
    return data


def read_document(source, commit, item):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show", f"{commit}:{item['source']}"],
        capture_output=True,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item["sha256"]:
        raise ConfigurationError("GISDS source unavailable or checksum mismatch; check GISDS_SOURCE.")
    return result.stdout.decode("utf-8")


def on_files(files, config):
    data = manifest()
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and not os.environ.get("GISDS_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require GISDS_SOURCE.")
    source = Path(os.environ.get("GISDS_SOURCE", str(ROOT.parent / "ecological-information/GISDS"))).expanduser()
    if any(f.src_uri in EXPECTED.values() for f in files):
        raise ConfigurationError("GISDS publication destination already exists.")
    for item in data["documents"]:
        content = read_document(source, data["commit"], item)
        files.append(File.generated(config, item["page"], content=content))
    return files


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        # Website navigation only: do not edit or duplicate the umbrella manuscript.
        return markdown + OVERVIEW_NAV
    if page.file.src_uri == CATALOGUE:
        # The complete source table follows verbatim, without rewriting any cell.
        return "# GISDS — Resource catalogue\n\n[Research guide, academic attribution and reuse guidance](research-guide.md)\n\n" + markdown
    if page.file.src_uri == GUIDE:
        data = manifest()
        markdown = markdown.replace("](GISDS.md)", "](index.md)")
        for name in ["CITATION.cff", "CHANGELOG.md"]:
            markdown = markdown.replace(f"]({name})", f"]({data['repository']}/blob/{data['commit']}/{name})")
        return markdown
    return markdown
