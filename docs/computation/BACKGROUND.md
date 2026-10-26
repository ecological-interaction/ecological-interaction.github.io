<!-- Generated from ecological-computation/BACKGROUND.md; edit the source and rerun scripts/export_website.py. -->

# Ecological Computation — background

Ecological Computing is the computational methods and data-processing
domain of the Ecological Interaction ecosystem.

Its purpose is to provide reusable tools for processing ecological
information through reproducible scientific workflows.

## Relationship to Ecological Information

Ecological Information organises research references, indicators,
classifications, datasets and metadata.

Ecological Computing processes data using explicit methods, input
assumptions and output conventions. Computational outputs should retain
enough provenance to connect them to their source data and method.

Computing supports the wider ecosystem: Understanding teaches methods,
Intelligence interprets results, Infrastructure enables access and
deployment, and Generation uses methods and evidence to evaluate
interventions.

## Current project catalogue

### conir_to_ndvi_image

Single-image processing using an assumed cyan/orange/NIR channel mapping.
It calculates an experimental NIR–Orange normalised difference index
and produces a colour visualisation.

The assumed sensor mapping and orange-band substitution require explicit
documentation and validation. The output is not evidence of calibrated
conventional red-band NDVI.

### rgb_to_exg_video

RGB video processing using raw-channel Excess Green:

`2G - R - B`

The implementation produces a false-colour video from the calculated
index and selected display range.

### rgb_to_grvi_video

RGB video processing using the Green-Red Vegetation Index:

`(G - R) / (G + R)`

The implementation includes optional preprocessing and visualisation
controls. Experimental and backup implementations, and a manual frame
diagnostic, remain part of the development repository.

### soil_organic_carbon

An existing empty ordinary directory. Its scope remains to be defined;
it is not an established Git repository or implemented software project.

## Repository boundaries and reproducibility

The three processing tools are independent sibling Git repositories.
Each has its own package metadata, uv lockfile, Python-version
configuration and local environment.

This umbrella contains the domain catalogue and shared conventions.
It does not contain copies of project source code or research datasets.

The containing `ecological-computing/` directory is an ordinary
organisational directory.

Each project should remain independently downloadable and usable.
Shared conventions do not require a common runtime package.

[SUITE.md](SUITE.md) records formulas, channel assumptions, software
structure, external dependencies, limitations and development requirements.
Project-specific usage instructions remain in each project's own README
and workspace brief.

Public project links are withheld pending availability; see LANDING.md for the current check.

## Broader domain scope

Future work may include:

- GIS and spatial computation.
- Remote-sensing and multispectral processing.
- Bioinformatics processing.
- Environmental sensor-data processing.
- Reusable command-line tools.
- Reproducible notebooks and computational teaching examples.

These are domain directions, not claims that those capabilities already
exist in the current repositories.

## Scientific validation and development status

All three processing repositories have initial development commits.
They contain source implementations and documentation scaffolds, but
their presence does not establish scientific calibration, supported
platforms or production readiness.

Before release, validate numerical behaviour, input assumptions,
dependency resolution, installed commands and representative end-to-end
workflows. Distinguish numerical index values from clipped, scaled or
colour-mapped display outputs.

CONIR and GRVI installed commands currently call greeting stubs.
GRVI processing executes at module level. Automated numerical test
suites and complete redistributable examples remain future work.

Functional repairs and scientific changes require separate development
tasks. Establishing this umbrella does not modify processing algorithms.

Licensing, repository citation metadata and publication arrangements
remain to be agreed. The configured umbrella remote remains https://github.com/Jonathan-Minchin/ecological-computing.git; only the local directory has been renamed.
