project = "Rivora Contract Protocol"
author = "Bhavya Malhotra"
copyright = "2026, Bhavya Malhotra"

extensions = ["myst_parser", "sphinx_rtd_theme"]
myst_heading_anchors = 3
source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}
root_doc = "index"
exclude_patterns = ["documentation.md", "_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "Rivora Contract Protocol"
html_show_sourcelink = False
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 3,
    "sticky_navigation": True,
    "titles_only": False,
}
