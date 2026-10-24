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

## Ecological Information publication

The Information overview, DRM introduction, federation PNG and historical
reorganisation JSON are generated from the approved commit and SHA-256 allowlist
in `publications/information.json`. Their source remains the independent
`ecological-information/ecological-information` checkout; no editable academic
copies are maintained in this website. Only README link destinations are mapped
to MkDocs index paths; the image and historical JSON are copied byte-for-byte.

Set `INFORMATION_SOURCE` to another checkout or bare repository containing the
pinned commit if needed. GitHub Actions fetches it anonymously into
`.sources/ecological-information`. Changing source `main` alone does not advance
the published version: approve a new manifest commit and checksums explicitly.
EIRKB retains its separate source pin, importer and navigation. The generated
overview replaces the former website-owned Mermaid page.

Use the existing test/build commands above, then preview with
`uv run --no-sync mkdocs serve --dev-addr 127.0.0.1:8000` at
`http://127.0.0.1:8000/information/` and `/information/DRM/`.

## GISDS publication

`publications/gisds.json` pins the approved GISDS commit and checksums.
`README.md` supplies the Geographic Sources Overview at `/information/GISDS/`.
`GISDS.md` supplies its child `/information/GISDS/resource-catalogue/`, with
all 25 source rows retained verbatim and no diagram. `RESEARCH_NOTES.md`
supplies linked supporting guidance at `/information/GISDS/research-notes/`.
The former `/information/GISDS/research-guide/` route retains the detailed notes
and historical heading anchors. The former catalogue heading fragment remains
on the Overview beside its catalogue link. Citation and changelog links point
to the same pinned GitHub commit. The SVG is copied as verified bytes; the
source renderer is never executed during publication. No preview override or
uncommitted source is used by the production build.

The importer adds a catalogue/guide navigation link after the imported
Information overview without editing the umbrella manuscript. Existing
Information and EIRKB pins and source documents are independent and unchanged.
`GISDS_SOURCE` can select a checkout or bare repository containing the approved
commit; the local default is `../ecological-information/GISDS`. GitHub Actions
fetches the exact commit anonymously into `.sources/GISDS`, preserving automatic
Pages deployment on website `main` pushes. Source updates alone do not change
publication until a new manifest pin and checksums are approved.

Use the existing tests and strict build above. Preview with
`uv run --no-sync mkdocs serve --dev-addr 127.0.0.1:8000`, then open
`http://127.0.0.1:8000/information/GISDS/` and
`http://127.0.0.1:8000/information/GISDS/resource-catalogue/`.

## EII publication

`publications/eii.json` pins EII's approved source commit. The scientific register
and README are generated at `/information/EII/` and its `research-guide/` page.
Only local link targets and website navigation are adapted; indicator tables,
wording, classifications and scholarly references remain source-owned.
The Information overview gains a website navigation link without changing its
source manuscript or existing GISDS link.

The `machine-reference/` page links to the full authoritative machine reference
and raw Markdown at the same pinned commit. The remote-sensing subset is linked
from the guide at that commit. Both source-only references have checksums in
the manifest and are verified during builds; their research bodies are not
copied into website source or rendered as duplicate registers. The machine file
contains JSON fences inside Markdown and must not be parsed as standalone JSON.

The local default source is `../ecological-information/EII`; `EII_SOURCE` can
select another checkout or bare repository containing the approved commit.
GitHub Actions retrieves it anonymously into `.sources/EII`. The existing
Information, EIRKB and GISDS approval pins remain independent. Public access
does not assign a licence or grant reuse permissions.

Run the publication tests and strict build above, then preview with
`uv run --no-sync mkdocs serve --dev-addr 127.0.0.1:8000` at
`http://127.0.0.1:8000/information/EII/`, its `research-guide/` and
`machine-reference/` pages. Review before committing or pushing.

## OSDS publication

`publications/osds.json` pins approved OSDS commit
`48b5d7f131ae4b86557d4a7b58a1371cacd3cd6c` with SHA-256 checksums for three documents,
one authoritative machine reference and one SVG. README.md supplies the Overview
at `/information/OSDS/`; the Scientific Reference Register is its only sidebar
child at `/information/OSDS/scientific-reference-register/`. Supporting notes
are linked at `/information/OSDS/research-notes/`. The former `research-guide/`
route preserves the detailed notes and heading anchors. Old scientific heading
fragments on the landing page lead to its full-register link.

The legacy `machine-reference/` access page remains available without a sidebar
entry. Machine source bodies are never copied into website pages. Scientific
record links preserve all 62 `#src-NNN` fragments at the authoritative machine
file in the same pinned GitHub commit. Local document link destinations are
adapted; scientific tables, identifiers, source URLs and classifications remain
unchanged. The compact SVG is verified and copied byte-for-byte. The Mermaid
source and renderer are not imported or executed during builds.

Set `OSDS_SOURCE` to a checkout or bare repository containing the approved commit.
The local fallback is `../ecological-information/OSDS`; hosted builds require
an explicit source. GitHub Actions anonymously fetches the exact manifest pin
into `.sources/OSDS`. Missing sources, commits, allowlisted documents or matching
checksums stop the build. No temporary preview override is used in production.

Run the existing unittest suite and strict MkDocs build, then preview normally
with `uv run mkdocs serve` at `http://127.0.0.1:8000/information/OSDS/`.
No unrelated source pins or deployment settings are changed.

## Website branding and section navigation

The header uses the official Ecological Interaction GitHub organisation avatar,
retained without modification as `docs/assets/branding/ecological-interaction-logo.png`.
Source: https://avatars.githubusercontent.com/u/342349500?v=4&s=512,
verified against https://github.com/ecological-interaction on 24 October 2026.
The returned original is a 460 × 460 RGBA PNG; SHA-256:
`d265c8181b3c9a1eb4b5eb677ca9b5c99a27a82014de87ad1932157b8494de89`.
The organisation profile and website repository supplied no separate vector logo
or additional asset attribution. Do not replace the mark with a generated image.

Material's supported `navigation.indexes` feature links Information and each
nested database title to its existing `index.md`. The index is the first,
unlabelled section item, so no duplicate Overview, Introduction or catalogue
menu entry is rendered. Layers with only a landing page remain direct links;
use the same section-index pattern if child pages are added later. No theme
template override is required.

Native testing confirmed separate title links and disclosure arrows, but the
arrow labels had no accessible name and Space did not toggle consistently.
`docs/javascripts/navigation-accessibility.js` progressively gives those native
controls a button role, explicit name, controlled panel and synchronised expanded
state, and handles Enter/Space once. Material still controls layout, mobile
panels and checkbox navigation; all destination links remain native anchors.
No instant-navigation feature is enabled. Recheck this small enhancement when
upgrading Material. The home page retains a visually hidden h1, explicit metadata
and its original body content; `docs/stylesheets/site.css` supplies the hiding
and disclosure-focus styles.

Navigation/branding regression tests build the real site. The disclosure
interaction test uses Node.js' built-in test runner (no npm packages); Node is
available on GitHub's Ubuntu runner. Locally, put Node on PATH or set
`EI_TEST_NODE` to an existing executable when running the unittest suite.
