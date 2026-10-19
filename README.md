# ecological-interaction.github.io
Public website and documentation index for Ecological Interaction research, software, and applications.

## EIRKB publication

EIRKB research is imported from the full commit and document checksums in
`publications/eirkb.json`. The independent EIRKB checkout remains authoritative;
no editable copies of its research documents are stored in this website.

Normal MkDocs builds include the approved EIRKB introduction, Master document
and Reference Register. Using the existing uv environment, build locally:

```sh
uv run --no-sync mkdocs build --strict
```

Then launch it at `http://127.0.0.1:8000/information/EIRKB/`:

```sh
uv run --no-sync mkdocs serve --dev-addr 127.0.0.1:8000
```

The default source location is the sibling `ecological-information/EIRKB`
checkout. Set `EIRKB_SOURCE` to another local checkout if needed. Files are read
from the pinned commit, never from uncommitted source edits. A missing commit or
checksum mismatch stops the build. Normal output goes to `site/`. Optionally,
`EIRKB_PREVIEW=1` isolates local preview output in `site-preview/`; it is not
needed to include EIRKB and is rejected in GitHub Actions.

The workflow retains automatic Pages deployment on pushes to `main`, plus manual
dispatch. Once these changes are committed and pushed,
that workflow will publish the selected EIRKB documents. Review locally and obtain
publication approval before pushing. Advancing the EIRKB research branch does not
change the published version: update the manifest's commit and checksums only
after approving a new publication version.

The source-workbook link is resolved to its pinned location in the public EIRKB
repository. No workbook is imported.

## GitHub Actions public-source access

EIRKB is public. Its selected commit is fetched anonymously over HTTPS, with
credential helpers, authentication headers and interactive prompts disabled.
No token, GitHub App or Actions secret is used to retrieve EIRKB. The normal
GitHub Actions permissions remain necessary for the website checkout and Pages
deployment, independently of the public research-source retrieval.

The workflow reads the selected SHA from the manifest, fetches that commit into
the ignored `.sources/EIRKB` bare Git directory. It creates no research working
tree; the importer reads only the two approved documents from that commit.
Git objects remain outside `docs/` and
`site/`; only the allowlisted Markdown enters the Pages artifact. No research
code is executed, no source checkout is cached, and no workbook is imported.

A failed public checkout, unavailable commit or checksum mismatch stops the workflow
before artifact upload and deployment. The repository must keep Pages configured
to use GitHub Actions. Existing `github-pages` environment protection rules may
require separate approval.

Run the local checks with:

```sh
uv run --no-sync python -B -m unittest discover -s tests -v
uv run --no-sync mkdocs build --strict
```
