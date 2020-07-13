# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

import depthcharge

# -- Project information -----------------------------------------------------

project = 'Depthcharge'
copyright = '2019-2020, NCC Group'
author = 'Jon Szymaniak (NCC Group)'

# The full version, including alpha/beta/rc tags
release = depthcharge.__version__

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

autodoc_member_order = 'bysource'

# -- Options for HTML output -------------------------------------------------

html_static_path = ['_static']

# Apply RTD theme overrides
html_context = {
    'css_files': [
        '_static/theme_overrides.css'
    ],
}

html_logo = '../images/depthcharge-500.png'

html_theme = 'sphinx_rtd_theme'

html_theme_options = {
    'logo_only': True
}
