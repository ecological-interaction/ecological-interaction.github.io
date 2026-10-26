"""Exercise MkDocs' file-path hook loader without the test runner's sys.path."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MkDocsHookLoadingTests(unittest.TestCase):
    def test_diagram_hooks_load_in_isolated_python_from_another_directory(self):
        script = r'''
import importlib.util
from pathlib import Path
import sys
from mkdocs.config import load_config

config_path = Path(sys.argv[1]).resolve()
assert str(config_path.parent) not in sys.path
assert "scripts" not in sys.modules
assert importlib.util.find_spec("scripts") is None
config = load_config(str(config_path))
expected = {"eirkb_publication.py", "eii_publication.py", "gisds_publication.py"}
hooks = [hook for hook in config["hooks"].values() if Path(hook.__file__).name in expected]
assert len(hooks) == 3
asset = "assets/diagrams/example.svg"
block = f"![Diagram]({asset})\n\n[View full-size diagram]({asset})."
for hook in hooks:
    assert callable(hook.on_files)
    landing = {"eirkb_publication.py": "INTRODUCTION", "gisds_publication.py": "GUIDE", "eii_publication.py": "CATALOGUE"}[Path(hook.__file__).name]
    assert getattr(hook, landing).endswith("/index.md")
    assert not hasattr(hook, "diagram_markup")
assert str(config_path.parent) not in sys.path
print("All three diagram hooks loaded through MkDocs without the repository on sys.path.")
'''
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        with tempfile.TemporaryDirectory(prefix="mkdocs-hook-loading-") as directory:
            result = subprocess.run(
                [sys.executable, "-I", "-B", "-c", script, str(ROOT / "mkdocs.yml")],
                cwd=directory, env=env, capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("All three diagram hooks loaded through MkDocs", result.stdout)
