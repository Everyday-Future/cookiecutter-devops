======================
Cookiecutter DevOps
======================

Cookiecutter_ template for a DevOps project

* GitHub repo: https://github.com/Everyday-Future/cookiecutter-devops
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

Ensure that you have python 3.9+ installed and on your system path.

Install the latest Cookiecutter if you haven't installed it yet (this requires
Cookiecutter 2.0.0 or higher)::

# pipx is strongly recommended.
pipx install cookiecutter
# If pipx is not an option,
# you can install cookiecutter in your Python user directory.
python -m pip install --user cookiecutter

Unpack the repo template::

    cookiecutter https://github.com/Everyday-Future/cookiecutter-devops.git

THEN DO ALL OF THE FOLLOWING:

* run the ___setup.bat (Windows) or ___setup.sh (Linux/Mac) script, which creates a venv and installs the requirements in it
* run the CLI interface with .__run_cli.bat (Windows) or .__run_cli.sh (Linux/Mac)
* set up the frontend of your choice in the frontend directory. Make sure to keep the .env files in there
* update the Dockerfile-frontend to reflect the new frontend.
* if you're using pycharm, move one folder up, right-click on the folder, and select run as pycharm project.
* Assign the system interpreter for pycharm to the venv instance of python
* Download a version of chromedriver that matches your current version of Chrome from https://googlechromelabs.github.io/chrome-for-testing/#stable
