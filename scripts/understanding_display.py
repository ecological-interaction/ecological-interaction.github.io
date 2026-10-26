"""Central display vocabulary for domain cards, independent of courseware metadata."""
from functools import lru_cache
from importlib.resources import files

SUBJECTS = {
    'geography': ('Geography', '#2563EB'),
    'ecology': ('Ecology', '#15803D'),
    'biology': ('Biology', '#D97706'),
    'concept': ('Concept', '#7C3AED'),
    'practice': ('Practice', '#0F766E'),
}
APPROACHES = {
    'systems': ('Systems', 'graph-outline'),
    'technology': ('Technology', 'cog-outline'),
    'computation': ('Computation', 'code-braces'),
    'design': ('Design', 'pencil-ruler'),
}


@lru_cache(maxsize=4)
def approach_icon(approach):
    # Never accept a file path or SVG from source metadata.
    _, icon = APPROACHES[approach]
    svg = files('material').joinpath('templates', '.icons', 'material', icon + '.svg').read_text(encoding='utf-8')
    return svg.replace('<svg ', '<svg aria-hidden="true" focusable="false" ', 1)
