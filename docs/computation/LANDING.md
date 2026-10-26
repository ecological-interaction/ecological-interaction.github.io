<!-- Generated from ecological-computation/LANDING.md; edit the source and rerun scripts/export_website.py. -->

# Landing page maintenance

README.md is the single authored catalogue. Native HTML details/summary controls
work without JavaScript. GitHub displays a vertical disclosure list with full
wrapping titles; its sanitizer removes the custom styling. The website adds
compact equal-height summaries, ellipses, solid category dots and responsive
three/two/one-column grids. Titles remain in accessible text and title tooltips.

## Files and export

Umbrella-owned: README.md, BACKGROUND.md, SUITE.md, this guide,
web/computation.css and scripts/export_website.py.
Website-owned: mkdocs.yml, with one extra_css entry. Its computation Markdown
pages and stylesheets/computation.css are generated snapshots, not separately
authored catalogues. No new website dependency or JavaScript is needed.

After editing the source, regenerate the website snapshot:

```sh
python3 scripts/export_website.py /Users/jonathan/Github/ecological-interaction.github.io
```

The website must include stylesheets/computation.css under extra_css.
Snapshots let hosted builds work without access to a sibling checkout or an
unpublished commit. Review and commit the generated changes alongside the source.
The existing site navigation and publication hooks are retained.

## Public link checks — 2026-10-26

Anonymous HTTPS HEAD requests following redirects returned HTTP 404, with no
redirect, for all three configured destinations:

- `https://github.com/Jonathan-Minchin/rgb_to_grvi_video`
- `https://github.com/Jonathan-Minchin/rgb_to_exg_video`
- `https://github.com/Jonathan-Minchin/conir_to_ndvi_image`

These may be private or unavailable. They are not live catalogue publication
links. Verify availability again before replacing the unavailable-link labels.
No repository was renamed remotely and no remote URL was changed.

## Local rename

The umbrella now lives at ecological-computing/ecological-computation.
The containing directory and processing repositories retain their names.
In GitHub Desktop, if the repository is missing, choose Locate and select the
renamed directory. Alternatively use File → Add Local Repository and select it.
Do not clone or create a new repository. The displayed repository name may
continue to reflect the unchanged GitHub remote.

## Preview

In the website checkout, run `.venv/bin/mkdocs serve --dev-addr 127.0.0.1:8000`
and open http://127.0.0.1:8000/computation/. Nothing is deployed by this command.

## Verification — 2026-10-26

- Strict MkDocs build passed with existing publication hooks.
- Existing Python suite: 101 tests, OK, one skipped.
- Existing JavaScript navigation suite: four passed.
- Browser measurements: all 15 desktop cards 224 × 96 px; closed cards in
  the narrow view 428 × 96 px. No desktop metadata overflow.
- Pointer click, Enter and Space toggle the native disclosures; keyboard
  focus is visible and full titles remain in the accessibility tree.
- Desktop and mobile layouts were visually inspected. Physical touchscreen
  interaction was not tested; disclosures use native browser controls.
- GitHub uses a readable unstyled disclosure list. Live GitHub rendering
  has not been tested because these changes remain local and uncommitted.
- All Git metadata file hashes and refs matched the pre-rename snapshot.
- No source changes, commits, pushes, remote changes or deployments.
