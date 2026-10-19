"""Opt-in, pinned EIRKB preview. Normal and hosted builds import no research."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from mkdocs.exceptions import ConfigurationError
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
MARKER = "<!-- EIRKB_PREVIEW_LINK -->"
INTRODUCTION = "information/EIRKB/index.md"
REGISTER = "information/EIRKB/reference-register.md"
WORKBOOK = "registers/ecological_information_complete_reference_register_v0.1.xlsx"
_enabled = False
_manifest = None


def read_document(source, commit, document):
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
    return result.stdout.decode("utf-8")


def on_config(config):
    global _enabled, _manifest
    _enabled = os.environ.get("EIRKB_PREVIEW") == "1"
    _manifest = None
    if _enabled and os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise ConfigurationError(
            "EIRKB preview is local-only. Hosted publication needs separate approval."
        )
    if not _enabled:
        # The source nav describes the preview; ordinary builds retain Overview only.
        for section in config.nav:
            if "Information" in section:
                section["Information"] = [
                    item for item in section["Information"] if "EIRKB" not in item
                ]
        return config
    _manifest = json.loads((ROOT / "publications/eirkb.json").read_text())
    config.site_dir = str(ROOT / "site-preview")
    return config


def on_files(files, config):
    if not _enabled:
        return files
    source = Path(os.environ.get(
        "EIRKB_SOURCE", str(ROOT.parent / "ecological-information/EIRKB")
    )).expanduser()
    documents = _manifest["documents"]
    # Only the two approved research documents are eligible for import.
    expected = {
        "MASTER_history_theory_ecological_information.md":
            "information/EIRKB/history-and-theory.md",
        "EIRKB Reference Register.md": REGISTER,
    }
    if {d["source"]: d["page"] for d in documents} != expected or len(documents) != 2:
        raise ConfigurationError("Unexpected EIRKB research-document allowlist.")
    for document in documents:
        files.append(File.generated(
            config, document["page"],
            content=read_document(source, _manifest["commit"], document),
        ))
    files.append(File.generated(
        config, INTRODUCTION,
        content=(ROOT / "publications/eirkb-introduction.md").read_text(),
    ))
    return files


def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri == "information/index.md":
        link = (
            "[EIRKB — Ecological Information Reference Knowledge Base](EIRKB/index.md)\n\n"
            "History, intellectual lineages, conceptual maps and a reference register."
            if _enabled else ""
        )
        return markdown.replace(MARKER, link)
    if _enabled and page.file.src_uri == REGISTER:
        # Presentation-only link resolution; committed research bytes remain unchanged.
        # No unapproved workbook is copied into the site.
        destination = (
            f"{_manifest['repository']}/blob/{_manifest['commit']}/{WORKBOOK}"
        )
        return markdown.replace(f"]({WORKBOOK})", f"]({destination})")
    return markdown
