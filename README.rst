======================
Cookiecutter DevOps
======================

Cookiecutter_ template for a DevOps project

* GitHub repo: https://github.com/Steamboat/cookiecutter-devops
* Free software: BSD license

Features
--------

* Testing setup with ``unittest``
* GCP+Azure CI/CD: Ready for multiple build pipelines
* Jupyter Notebook: Includes architecture inspired by cookiecutter-data-science
* Sphinx_ docs: Documentation ready for generation with, for example, `Read the Docs`_
* Click: CLI for bumping version, loading servers, running tests, and more


Quickstart
----------

Install the latest Cookiecutter if you haven't installed it yet (this requires
Cookiecutter 1.4.0 or higher)::

    pip install -U cookiecutter

Generate a Python package project::

    cookiecutter https://github.com/Steamboat/cookiecutter-devops.git

Then:

* Create a repo and put it there.
* Add the repo to your Travis-CI_ account.
* Install the dev requirements into a virtualenv. (``pip install -r requirements.txt``)
* Register_ your project with PyPI.
* Run the Travis CLI command ``travis encrypt --add deploy.password`` to encrypt your PyPI password in Travis config
  and activate automated deployment on PyPI when you push a new tag to master branch.
* Add the repo to your `Read the Docs`_ account + turn on the Read the Docs service hook.
* Release your package by pushing a new tag to master.
* Add a ``requirements.txt`` file that specifies the packages you will need for
  your project and their versions. For more info see the `pip docs for requirements files`_.
* Activate your project on `pyup.io`_.

.. _`pip docs for requirements files`: https://pip.pypa.io/en/stable/user_guide/#requirements-files
.. _Register: https://packaging.python.org/tutorials/packaging-projects/#uploading-the-distribution-archives

For more details, see the `cookiecutter-pypackage tutorial`_.

.. _`cookiecutter-pypackage tutorial`: https://cookiecutter-pypackage.readthedocs.io/en/latest/tutorial.html


.. _Travis-CI: http://travis-ci.org/
.. _Tox: http://testrun.org/tox/
.. _Sphinx: http://sphinx-doc.org/
.. _Read the Docs: https://readthedocs.io/
.. _Mkdocs: https://pypi.org/project/mkdocs/
