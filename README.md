# ecological-interaction.github.io
Public website and documentation index for Ecological Interaction research, software, and applications.

## Local EIRKB review

EIRKB research is imported from the full commit and document checksums in
`publications/eirkb.json`. The independent EIRKB checkout remains authoritative;
no editable copies of its research documents are stored in this website.

Using the existing uv environment, build the local preview:

```sh
EIRKB_PREVIEW=1 uv run --no-sync mkdocs build --strict
```

Then launch it at `http://127.0.0.1:8000/information/EIRKB/`:

```sh
EIRKB_PREVIEW=1 uv run --no-sync mkdocs serve --dev-addr 127.0.0.1:8000
```

The default source location is the sibling `ecological-information/EIRKB`
checkout. Set `EIRKB_SOURCE` to another local checkout if needed. Files are read
from the pinned commit, never from uncommitted source edits. A missing commit or
checksum mismatch stops the build. Preview output is isolated in `site-preview/`.

Without `EIRKB_PREVIEW=1`, builds omit EIRKB navigation, research, links and search
entries. The existing automatic deployment workflow is unchanged and its normal
`site/` output contains no EIRKB content. The preview flag is rejected in GitHub
Actions. Do not manually upload or deploy `site-preview/` before publication approval.

The source-workbook link is resolved to its pinned location in the private EIRKB
repository; access is required. No workbook is imported.

Hosted import will require separately approved read access to private EIRKB
(a scoped GitHub App token or fine-grained token); the website's ordinary
`GITHUB_TOKEN` does not grant cross-repository private access. No credentials or
hosted-publication mode are configured here. A future approved publication mode
must preserve the explicit source commit and document allowlist.
