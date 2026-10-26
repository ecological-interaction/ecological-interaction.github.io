<!-- Generated from ecological-computation/SUITE.md; edit the source and rerun scripts/export_website.py. -->

# Ecological Computing — suite coordination

## Workspace boundaries

The suite currently consists of three independent software repositories:

| Project | Scope | Project-local workspace brief |
|---|---|---|
| conir_to_ndvi_image | Experimental NIR–Orange normalised difference index and visualisation | WORKSPACE.md |
| rgb_to_exg_video | Raw-channel Excess Green video | WORKSPACE.md |
| rgb_to_grvi_video | GRVI video and visualisation controls | WORKSPACE.md |

Each repository has its own working directory, package metadata,
environment, lockfile and Git history. Read its README, WORKSPACE.md,
pyproject.toml and processing source before project development.

This umbrella coordinates suite documentation and conventions.
The containing ecological-computing directory is an ordinary
organisational directory.

soil_organic_carbon is an existing empty ordinary directory.
ndvi_project, mentioned in earlier documentation, is absent from the
current workspace. Its previous contents or current location are not
established by this document.

## Current development status

The initial development commits are:

| Project | Initial commit |
|---|---|
| conir_to_ndvi_image | 3cc81a889817c93a6b322b0fa6c39460631b3ad4 |
| rgb_to_exg_video | 33e8e5f9ae76d82577871284fa6c6fb5f2f2599a |
| rgb_to_grvi_video | 3122d2bddf9cca13bc7e93387fcd22873e1247e6 |

All three projects have configured GitHub remotes. Anonymous HTTP checks on
2026-10-26 returned 404 for each project URL; see LANDING.md. This does not
establish whether the repositories are private or unavailable.

Test, documentation, notebook and sample directories contain scaffolding
guidance. They do not establish an automated test suite or complete
redistributable example set.

The previously identified generated GRVI MP4 is absent. The GRVI
project's WORKSPACE.md still contains a historical statement that it
exists; correcting that project document requires a separate approved task.

Existing source, diagnostic, experimental and backup implementations
remain preserved. None is removed or modified by umbrella creation.

## Scientific methods and assumptions

### CONIR image processing

After OpenCV loads the image in BGR order, the implementation assumes:

- Blue represents cyan.
- Green represents orange.
- Red represents NIR.

It calculates an experimental NIR–Orange normalised difference index:

`(NIR - Orange) / (NIR + Orange + 1e-6)`

and clips the result to [-1, 1].

This uses an assumed orange/NIR mapping, not calibrated conventional
red-band NDVI. Document and validate the sensor response and channel
interpretation before scientific use.

The visualisation uses RdYlGn. When display bounds are omitted, the
implementation uses the 5th and 95th percentiles. An optional colour
scale can be included.

### Excess Green video processing

The implementation converts OpenCV BGR channels to floating point
and calculates:

`ExG = 2G - R - B`

It uses raw channels; it does not normalise RGB by their sum.

Default display bounds are -100 to 200, using the Turbo palette.
These bounds control visualisation and do not redefine the index.

### GRVI video processing

The implementation converts red and green channels to floating point
and calculates:

`GRVI = (G - R) / (G + R)`

Zero-denominator pixels are assigned zero.

Default display bounds are -0.2 to 0.4, with Turbo as the default palette.

Optional denoising and Gaussian blur occur before index calculation
and can change calculated values. Colour-map selection and inversion
affect display. The shadow threshold masks low-brightness pixels in
the displayed output.

GRVI retains an OpenCV mp4v backup implementation and an FFmpeg
experimental implementation with a default CRF of 0. These are
development variants, not automatically equivalent supported interfaces.

## Dependencies and command-line interfaces

All three projects declare Python >=3.9 and use a .python-version
setting of 3.9. Compatibility must be validated rather than inferred
from these declarations.

Python dependencies include NumPy and OpenCV. CONIR also uses Matplotlib.

The main ExG and GRVI video processors require an external FFmpeg
executable with libx264 support. Their output is video-only H.264
using yuv444p. Audio is omitted, and playback compatibility requires
validation.

The main video processors default to CRF 15.

Current command-line options include:

| Project | Options |
|---|---|
| CONIR | --input, --output, --vmin, --vmax, --scale |
| ExG | --input, --output, --vmin, --vmax, --crf |
| GRVI | --input, --output, --vmin, --vmax, --crf, --blur, --shadow-threshold, --colormap, --denoise, --invert-colormap |

CONIR and GRVI installed console commands currently point to greeting
stubs. Their processing scripts are separate implementations.

ExG's installed console command points to its processing main function.
GRVI's main processing module executes at import time.

Do not present installed commands as validated merely because package
entry points exist.

## Standard software structure

```text
<project>/
├── pyproject.toml
├── uv.lock
├── .python-version
├── src/<package>/
├── tests/
├── docs/
├── notebooks/
├── samples/
├── data/
│   ├── raw/
│   └── processed/
└── outputs/
```

Use src for reusable processing code, tests for automated verification,
docs for methods and usage, notebooks for exploration, and samples for
small redistributable inputs.

Preserve original inputs in data/raw, intermediates in data/processed,
and generated results in outputs. These local data and output locations
are ignored except for their approved placeholders and documentation.

Full recordings and research datasets may remain in external storage.
Record their provenance, reuse conditions and recovery requirements.

The standard layout does not redirect script paths automatically.
GRVI's manual grvi_frame_test.py diagnostic uses absolute external
Dropbox paths and is not a portable automated test.

Each project uses its own uv environment and lockfile.
Run environment and Git commands inside the relevant project repository.

## Input, output and provenance conventions

Document input encoding, channel order, sensor assumptions and supported
formats. Distinguish calculated numerical values from rendered
visualisations, clipping and display scaling.

Record source-data identity, software version, processing parameters
and relevant spatial or temporal metadata alongside research outputs.

Do not infer calibrated measurements or indicator validity solely
from successful image or video conversion.

Keep index-specific formulas, units, defaults and assumptions visible.
Shared option names should have consistent meanings where appropriate,
without forcing identical numerical ranges or features.

## Functional limitations and separate development tasks

- Connect CONIR and GRVI installed commands to their processing implementations.
- Make GRVI processing import-safe.
- Validate supported Python versions, dependency resolution and package builds.
- Test numerical behaviour, display bounds, constant inputs and channel assumptions.
- Review video dimensions, FPS, missing FFmpeg, encoder failures and cleanup.
- Document omitted audio and video playback compatibility.
- Prepare small end-to-end examples with clear provenance and reuse conditions.
- Define the supported role of experimental implementations and diagnostics.
- Correct stale project documentation through separately approved changes.

These tasks are not implemented by establishing the umbrella.

## Shared publication direction

Retain independent packages and commands, presented together under
Ecological Computing.

Align documentation structure, installation instructions, option
meanings, output conventions, diagnostics, examples and release quality.
Preserve each index's formula, units, sensor assumptions and appropriate
display range.

Do not introduce a shared runtime package until a concrete need warrants it.

Keep essential end-user documentation within each project so it remains
usable when downloaded independently. Changes to another project require
their own explicit scope.

Before release, agree on licensing, publication destination, supported
environments, versioning policy and citation metadata. Validate numerical
tests, installed commands and representative workflows.

A development baseline commit does not establish release readiness.

## Historical inspection — 2026-09-28

The following findings describe the earlier inspection, not the current
Git commit status or current app registration:

All three contain uv-based package metadata, lockfiles, src layouts,
local virtual environments, and Git directories. No Git remotes are
configured. At the time of that inspection, the project files
had not yet been committed to their respective Git
repositories. Test directories
currently contain scaffolding documentation, not automated suites.

CONIR and GRVI installed commands point to greeting stubs. ExG points
to its processing main function. GRVI's main processing module runs at
import time. Both video processors invoke FFmpeg, but their validation
and failure handling differ. CONIR uses an assumed orange/NIR mapping
and percentile display scaling for its experimental NIR–Orange normalised
difference index. ExG uses unnormalized `2G-R-B`; GRVI
uses `(G-R)/(G+R)`. These differences must be documented rather than
hidden by a uniform interface.

This inspection did not run conversions, install dependencies, modify
source, or establish scientific calibration or release readiness.

At that inspection, the coordination document reported only the parent
Ecological Computing folder as a registered Codex local project. It
also reported limitations in the available registration and computer
control tools. These were observations about that session, not permanent
claims about Codex capabilities.

For focused development, open the relevant individual repository.
A workspace brief provides context; it does not itself register a
local app project.

## Documentation preservation

This umbrella's first commit preserves the original parent README.md
and SUITE.md byte-for-byte.

The revised README provides domain orientation. This document retains
technical methods, software conventions and historical inspection
context while distinguishing current development status.

The original documents remain accessible through Git history.
