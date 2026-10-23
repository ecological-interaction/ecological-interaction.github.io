"""Publish only commit-pinned Information documents and assets, without source copies."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from mkdocs.exceptions import ConfigurationError
from mkdocs.plugins import event_priority
from mkdocs.structure.files import File

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/ecological-interaction/ecological-information"
EXPECTED = {
    "README.md": "information/index.md",
    "ARCHITECTURE.md": "information/architecture.md",
    "DRM/README.md": "information/DRM/index.md",
    "assets/diagrams/federated-knowledge-systems.png":
        "information/assets/diagrams/federated-knowledge-systems.png",
    "assets/diagrams/federated_knowledge_systems.svg":
        "information/assets/diagrams/federated_knowledge_systems.svg",
    "REORGANISATION.json": "information/REORGANISATION.json",
}


def manifest():
    data = json.loads((ROOT / "publications/information.json").read_text())
    if data.get("repository") != REPOSITORY or not re.fullmatch(
        r"[0-9a-f]{40}", data.get("commit", "")
    ):
        raise ConfigurationError("Information requires the approved repository and full commit SHA.")
    entries = data.get("files", [])
    if len(entries) != len(EXPECTED) or {
        item["source"]: item["page"] for item in entries
    } != EXPECTED or any(not re.fullmatch(r"[0-9a-f]{64}", item.get("sha256", "")) for item in entries):
        raise ConfigurationError("Unexpected Information publication allowlist or checksum.")
    return data


def read_file(source, commit, item):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(source), "show", f"{commit}:{item['source']}"],
        capture_output=True,
    )
    if result.returncode or hashlib.sha256(result.stdout).hexdigest() != item["sha256"]:
        raise ConfigurationError("Information source unavailable or checksum mismatch; check INFORMATION_SOURCE.")
    return result.stdout


def on_files(files, config):
    data = manifest()
    hosted = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"
    if hosted and not os.environ.get("INFORMATION_SOURCE", "").strip():
        raise ConfigurationError("Hosted builds require INFORMATION_SOURCE.")
    source = Path(os.environ.get(
        "INFORMATION_SOURCE", str(ROOT.parent / "ecological-information/ecological-information")
    )).expanduser()
    if any(f.src_uri in EXPECTED.values() for f in files):
        raise ConfigurationError("Information publication destination already exists.")
    for item in data["files"]:
        content = read_file(source, data["commit"], item)
        if item["source"].endswith(".md"):
            content = content.decode("utf-8")
            if item["source"] == "README.md":
                content = content.replace("](DRM/README.md)", "](DRM/index.md)")
                content = content.replace("](ARCHITECTURE.md)", "](architecture.md)")
            elif item["source"] == "ARCHITECTURE.md":
                content = content.replace("](README.md)", "](index.md)")
            else:
                content = content.replace("](../README.md)", "](../index.md)")
        files.append(File.generated(config, item["page"], content=content))
    return files


# Run after the existing database hooks, without changing their source content.
@event_priority(-100)
def on_page_markdown(markdown, page, **kwargs):
    if page.file.src_uri != "information/index.md":
        return markdown
    for project, addition in {
        "GISDS": "\n\n---\n\n[Browse the GISDS catalogue and research guide](GISDS/index.md)\n",
        "EII": "\n\n[Browse the EII scientific catalogue and research guide](EII/index.md)\n",
        "OSDS": "\n\n[Browse the OSDS scientific catalogue and research guide](OSDS/index.md)\n",
    }.items():
        # Keep fallback links if a later source edition removes its directory link.
        if f"](https://ecological-interaction.github.io/information/{project}/)" in markdown:
            markdown = markdown.replace(addition, "")
    return markdown
