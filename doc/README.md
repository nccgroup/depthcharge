# Depthcharge Documentation


This directory contains the source code for Depthcharge's documentation.  
If you're just looking for documentatoin to reference, see 
<https://depthcharge.readthedocs.io>.

## Dependencies

[GNU Make], [Sphinx] document generator, and the [ReadTheDocs.org theme] are
required to build the HTML documentation. The latter two items can be
installed via PIP.

```
$ pip install sphinx sphinx_rtd_theme
```

**Important:** If you are working with Depthcharge in a [venv], you
must install Sphinx (and `sphinx_rtd_theme`) within that environment,
even if you already have it installed on system through other package managers.
Otherwise, `sphinx-build` will fail to locate the `depthcharge` module present
only in your virtual environment.

## Build

With the above dependancies satisfied, the documentation can be created by running:

```
$ make html
```

Build artifacts will be saved in `build/`, with the
top-level landing page residing at `build/html/index.html`.

[GNU Make]: https://www.gnu.org/software/make
[Sphinx]: https://www.sphinx-doc.org/en/stable
[ReadTheDocs.org theme]: https://github.com/readthedocs/sphinx_rtd_theme
[venv]: https://docs.python.org/3/library/venv.html
