import sys
from pathlib import Path

project = "lunapi"
author = "lunapi maintainers"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}
autodoc_mock_imports = [
    # native extension
    "lunapi.lunapi0",
    # heavy/runtime deps not needed to render API docs
    "pandas",
    "numpy",
    "scipy",
    "scipy.stats",
    "scipy.stats.mstats",
    "scipy.signal",
    "matplotlib",
    "matplotlib.pyplot",
    "matplotlib.cm",
    "plotly",
    "plotly.graph_objects",
    "plotly.express",
    "ipywidgets",
    "IPython",
    "IPython.core",
    "IPython.core.display",
    "IPython.display",
    "requests",
    "tqdm",
    "tqdm.auto",
]

napoleon_google_docstring = False
napoleon_numpy_docstring = True

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
html_static_path = ["_static"]
