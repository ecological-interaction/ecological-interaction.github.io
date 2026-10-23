"""Import only approved EIRKB documents, pinned by commit and checksum."""

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
MARKER = "<!-- EIRKB_PREVIEW_LINK -->"
INTRODUCTION = "information/EIRKB/index.md"
REGISTER = "information/EIRKB/reference-register.md"
WORKBOOK = "registers/ecological_information_complete_reference_register_v0.1.xlsx"
_manifest = None


def read_file(source, commit, document):
    """Read committed bytes only; never execute or copy a source working tree."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ConfigurationError("EIRKB publication requires a full commit SHA.")
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show",
         f"{commit}:{document['source']}"],
        capture_output=True,
    )
    if result.returncode:
        raise ConfigurationError(
            "The selected EIRKB commit/document is unavailable locally. "
            "Set EIRKB_SOURCE to an accessible checkout containing the pinned commit."
        )
    if hashlib.sha256(result.stdout).hexdigest() != document["sha256"]:
        raise ConfigurationError("EIRKB document checksum differs from the approved manifest.")
    return result.stdout


def read_document(source, commit, document):
    return read_file(source, commit, document).decode("utf-8")


ASSETS = {"assets/diagrams/eirkb_overview.svg": "information/EIRKB/assets/diagrams/eirkb_overview.svg"}


def manifest(data=None):
    if data is None:
        data = json.loads((ROOT / "publications/eirkb.json").read_text())
    expected = {
        "MASTER_history_theory_ecological_information.md": "information/EIRKB/history-and-theory.md",
        "EIRKB Reference Register.md": REGISTER,
    }
    documents, references, assets = (data.get(key, []) for key in ["documents", "references", "assets"])
    if (data.get("repository") != "https://github.com/ecological-interaction/EIRKB"
            or not re.fullmatch(r"[0-9a-f]{40}", data.get("commit", ""))
            or len(documents) != 2 or {d["source"]: d["page"] for d in documents} != expected
            or len(references) != 1 or {d["source"] for d in references} != {"README.md"}
            or len(assets) != 1 or {d["source"]: d["page"] for d in assets} != ASSETS
            or any(not re.fullmatch(r"[0-9a-f]{64}", d.get("sha256", "")) for d in documents + references + assets)):
        raise ConfigurationError("Unexpected EIRKB repository, commit, allowlist or checksum.")
    return data


def on_config(config):
    global _manifest
    _manifest = None
    hosted = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    preview = os.environ.get("EIRKB_PREVIEW") == "1"
    if preview and hosted:
        raise ConfigurationError(
            "EIRKB_PREVIEW is local-only; hosted builds must use the normal site output."
        )
    if hosted and not os.environ.get("EIRKB_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require the approved EIRKB checkout at EIRKB_SOURCE.")
    _manifest = manifest()
    if preview:
        config.site_dir = str(ROOT / "site-preview")
    return config


def on_files(files, config):
    source = Path(os.environ.get(
        "EIRKB_SOURCE", str(ROOT.parent / "ecological-information/EIRKB")
    )).expanduser()
    data = manifest(_manifest)
    documents = data["documents"]
    if any(f.src_uri in {*ASSETS.values(), INTRODUCTION, *(d["page"] for d in documents)} for f in files):
        raise ConfigurationError("EIRKB publication destination already exists.")
    for document in documents:
        files.append(File.generated(
            config, document["page"],
            content=read_document(source, _manifest["commit"], document),
        ))
    readme = read_document(source, data["commit"], data["references"][0])
    diagram = diagram_markup(readme, next(iter(ASSETS)))
    for item in data["assets"]:
        files.append(File.generated(config, item["page"], content=read_file(source, data["commit"], item)))
    introduction = (ROOT / "publications/eirkb-introduction.md").read_text()
    introduction = re.sub(r"`[0-9a-f]{40}`", f"`{data['commit']}`", introduction, count=1)
    title, newline, body = introduction.partition("\n")
    files.append(File.generated(config, INTRODUCTION, content=title + "\n\n" + diagram + "\n" + body))
    return files


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        link = (
            "[EIRKB — Ecological Information Reference Knowledge Base](EIRKB/index.md)\n\n"
            "History, intellectual lineages, conceptual maps and a reference register."
        )
        return markdown.replace(MARKER, link)
    if page.file.src_uri == REGISTER:
        # Presentation-only link resolution; committed research bytes remain unchanged.
        # No unapproved workbook is copied into the site.
        destination = (
            f"{_manifest['repository']}/blob/{_manifest['commit']}/{WORKBOOK}"
        )
        return markdown.replace(f"]({WORKBOOK})", f"]({destination})")
    return markdown
