"""Extract the reviewed README diagram block without inventing website wording."""

import re
from mkdocs.exceptions import ConfigurationError


def diagram_markup(readme, asset):
    path = re.escape(asset)
    match = re.search(
        r"\A#[^\n]+\n\n(!\[[^\n]*\]\(" + path
        + r"\)\n\n[^\n]*\[View full-size diagram\]\(" + path + r"\)\.)\n",
        readme,
    )
    if not match:
        raise ConfigurationError("Pinned README diagram embedding or full-size link is missing.")
    return match.group(1)
