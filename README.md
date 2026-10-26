# ecological-interaction.github.io
Public website and documentation index for Ecological Interaction research, software, and applications.

## EIRKB publication

EIRKB is imported from the exact commit and per-file SHA-256 checksums in
`publications/eirkb.json`. Its README supplies `/information/EIRKB/`, including
the federation diagram and complete References, Concepts and People Index tables.
DRM remains available at `/information/DRM/` through contextual links, outside
the dropdown navigation. The student-facing EIRKB label remains Philosophical Approaches, with A01–A03
as its only sidebar children. Scientific register, machine reference and research
protocol routes remain available for compatibility, outside the sidebar. The source
README introduction provides concise GitHub links to these three resources.

Reading routes include `scientific-reference-register/`, `research-protocol/`,
`historic-arc/`, `intellectual-lineages/` and `intellectual-map/`.
`machine-reference/` offers the authoritative `EIRKB_Machine_Reference.json`
download; the original JSON bytes, schema, preservation crosswalk and CITATION.cff
are copied without changes. Source Markdown remains authoritative for authored
prose. No release, licence, DOI or DRM conformance is added by publication.

The existing `reference-register/` route retains the scientific tables and
bridges its historical Guide and Migration anchors to the protocol/changelog.
`history-and-theory/` publishes the source compatibility index, with preserved
historical heading and explicit-anchor links into A01–A03 and the changelog.
Workbooks are not imported. Existing workbook links resolve to `_legacy registers/`
at the same pinned GitHub commit; historical path strings in prose remain intact.

Both reviewed SVGs are copied byte-for-byte. Their Mermaid sources and renderers
are checksummed as source-only references, never executed or published as code.
The former website-owned `publications/eirkb-introduction.md` template is retained
as history but no longer supplies the landing page. No independent academic copy
is maintained in website docs.

Use the existing environment:

```sh
uv run python -B -m unittest discover -s tests -v
uv run mkdocs build --strict
uv run mkdocs serve --dev-addr 127.0.0.1:8000
```

Preview at `http://127.0.0.1:8000/information/EIRKB/`. Set `EIRKB_SOURCE` to an
approved checkout or bare repository when needed; hosted builds require it.
The local fallback is `../ecological-information/EIRKB`. Reads always use the
manifest commit, never uncommitted files. `EIRKB_PREVIEW=1` can isolate output in
`site-preview/` locally and remains forbidden in GitHub Actions. Missing sources,
checksums, unsupported destinations or invalid JSON reject the build.

Other publication pins and deployment settings remain independent. Source main
advancing alone does not change publication; a new pin/checksum approval is needed.

## GitHub Actions public-source access

EIRKB is public. Its selected commit is fetched anonymously over HTTPS, with
credential helpers, authentication headers and interactive prompts disabled.
No token, GitHub App or Actions secret is used to retrieve EIRKB. The normal
GitHub Actions permissions remain necessary for the website checkout and Pages
deployment, independently of the public research-source retrieval.

The workflow reads the selected SHA from the manifest, fetches that commit into
the ignored `.sources/EIRKB` bare Git directory. It creates no research working
tree; the importer reads only the explicitly allowlisted documents, downloads and
source-only diagram references from that commit.
Git objects remain outside `docs/` and
`site/`; only allowlisted Markdown, assets and downloads enter the Pages artifact. No research
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

`publications/eii.json` pins the reviewed EII source revision and all imported or
linked reference checksums. README.md supplies `/information/EII/` directly,
including its single SVG, introduction, Reading Key, Domain Index, complete
Consolidated Information Register, Observation Platforms and citation footer.
Only working link destinations and compatibility anchors are adapted; source
tables, wording, ordering and scientific qualifications remain source-owned.

The Material section-index label is Indicator Inventory. Its
only navigation children are EII — Remote Sensing (`remote-sensing/`) and
EII — Observational Systems (`observational-systems/`). The latter preserves the
approved empty research placeholder. `research-guide/` remains a compatibility
page linking to the landing page, while `machine-reference/` links to the JSON
authority and human-readable Scientific Register on GitHub. Earlier landing and
Research Guide anchors are retained without introducing duplicate menu entries.

The Scientific Register, JSON, Research Protocol, citation, changelog, schema,
preservation crosswalk and old machine Markdown pointer are verified source-only
references, not full website pages or duplicate hosted research corpora. README
supporting-file GitHub links are pinned to the approved commit. Remote Sensing
links to scientific records retain their fragments at that pinned GitHub source;
links within the subset remain local. Encoded and unencoded space-containing
filenames are mapped explicitly. Fenced code and inline-code provenance are not
rewritten. Mermaid and renderer bytes are checksummed but never executed; the
committed SVG is copied verbatim.

Set `EII_SOURCE` to an approved checkout or bare repository containing the exact
manifest commit. The local fallback is `../ecological-information/EII`; hosted
builds require the explicit source retrieved anonymously into `.sources/EII`.
Missing sources, changed checksums, invalid JSON, unapproved paths or duplicate
destinations reject the build. Source main advancing alone never advances a pin.
Other database publications and the automatic deployment workflow are unchanged.

Run the complete tests and strict build above, then preview with
`uv run mkdocs serve --dev-addr 127.0.0.1:8000` at
`http://127.0.0.1:8000/information/EII/`. Review before committing or pushing.

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

## Understanding publication and local review

`publications/understanding.json` pins the public organisation source repository,
full commit SHA and SHA-256 hashes for 14 files: the README, ten domain pages,
architecture overview, interface specification and candidate-inventory explanation.
Normal builds read only these Git objects into an isolated temporary snapshot.
Uncommitted source changes cannot affect production; missing commits or invalid
checksums stop the build with no draft fallback. Source Markdown remains authoritative.

The landing page at `/understanding/` uses the approved compact cards, source-owned
summaries, five subject classifications and four approach icons. Linked supporting
pages are included; source-only provenance and raw inventory links target GitHub at
the same exact commit. Local audit paths are redacted from rendered supporting
pages. Synthetic examples and review packages do not enter production output.

GitHub Actions anonymously fetches the exact selected commit into
`.sources/ecological-understanding`, checks it out for source metadata tests, and
sets `UNDERSTANDING_SOURCE` explicitly for tests and builds. Credential helpers,
authentication headers, global Git configuration and interactive prompts are disabled
for retrieval. No source code is executed. The importer reads verified Git objects,
not the checkout files. Other research-layer publication pins remain independent.

For a production-pinned local preview:

```sh
uv sync --frozen
uv run python -B -m unittest discover -s tests -v
UNDERSTANDING_DRAFT_PREVIEW=0 uv run mkdocs build --strict
UNDERSTANDING_DRAFT_PREVIEW=0 uv run mkdocs serve --dev-addr 127.0.0.1:8781
```

Open `http://127.0.0.1:8781/understanding/`. `UNDERSTANDING_SOURCE` can override
the default source Git repository at
`/Users/jonathan/Github/ecological-understanding/ecological-understanding`; a bare
repository also works for production import. Hosted builds require an explicit source.

For an isolated, opt-in working-tree draft preview:

```sh
UNDERSTANDING_DRAFT_PREVIEW=1 uv run mkdocs build --strict
UNDERSTANDING_DRAFT_PREVIEW=1 uv run mkdocs serve --dev-addr 127.0.0.1:8780
```

The default draft build writes to `site-understanding-preview/`, separately from
normal deployable `site/` output. Hosted GitHub Actions rejects draft mode. Drafts
validate domains, separate candidate metadata and resource relationship graphs using
PyYAML and JSON Schema Draft 2020-12 with format checking. Synthetic examples are
shape-checked but never registered. No reviewed courseware records exist; adding
real resources requires a separately reviewed publication allowlist.

Source `main` advancing alone does not update the website. Review the exact source
commit and checksums before changing this manifest. A website push to `main` triggers
the existing Pages deployment workflow; keep publication changes unpushed until review.
