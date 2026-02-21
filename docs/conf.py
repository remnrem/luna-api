import sys
from pathlib import Path

project = "lunapi"
author = "lunapi maintainers"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "autoapi.extension",
]

napoleon_google_docstring = False
napoleon_numpy_docstring = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Parse the source tree directly; no module import required.
autoapi_type = "python"
autoapi_dirs = [str(ROOT / "src" / "lunapi")]
autoapi_member_order = "bysource"
autoapi_keep_files = True
autoapi_add_toctree_entry = False

autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
]

html_theme = "alabaster"
html_static_path = ["_static"]
