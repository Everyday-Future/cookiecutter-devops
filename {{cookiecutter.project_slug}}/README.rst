
{% for _ in cookiecutter.project_name %}={% endfor %}
{{ cookiecutter.project_name }}
{% for _ in cookiecutter.project_name %}={% endfor %}


Description
============

{{ cookiecutter.project_short_description }}


Requirements
============

In order to run all of the functions of this codebase, you'll need:
- At least 1GB of space
- At least 2GB of RAM

Follow the instructions below to get everything set up and running on your machine.

Required Programs
-----------------

This project only requires 2 programs to work - docker and git.
Docker is used to create "containerized" environment for services to make everything cross-platform.
Git is used to pull down, save, and commit changes to code.

Therefore, the code itself is managed with git and run with docker.

Docker can be downloaded here - https://www.docker.com/products/docker-desktop
Git can be downloaded here - https://git-scm.com/downloads

Once you get git all set up, use it to clone this repo so that you can work with it locally.

Required Files
--------------

In addition to the programs listed above, there are a few files you'll need in order to run the program correctly.

Edit the secret--template.env and matching values files to remove the .txt

Then add any secrets that you'd like to include. Finally, recompile the .env files for each environement using the
env secret compiler (e) in the command-line interface.

Command-Line Interface
----------------------

Once the requirements are all set up, just run the __run_cli file appropriate for your system
(.bat for Windows, .sh for Linux/Mac). This is the menu for the codebase which will allow you to do all of the most
common maintenance tasks quickly and easily.

Use the server menu to start different versions of the app (or jupyter notebook). The testing menu allows different
tests to be run locally and is a good way to verify that everything is set up correctly. migrations are for database
migrations, which change the db structure.


Project Organization
====================
.. code::
    |-- __run_cli            <- Run the command-line interface (.bat for Windows, .sh for Linux/Mac)
    |-- README.rst           <- This top-level README for developers using this project.
    |-- data
    |   |-- raw              <- Raw data used to build prototypes
    |   |-- models           <- Trained or downloaded ML models
    |   |-- test_assets      <- Assets used for testing to be committed to the codebase
    |   |-- test_gallery     <- Assets created from notebooks or processing. Not committed to code.
    |   |-- reports          <- Ad hoc reports from notebooks and testing
    |
    |-- core                 <- Core python functionality for the app
    |   |
    |   |-- adapters         <- Interchangeable adapters to interact with cloud services
    |   |   |-- alert        <- Push notifications with Slack and/or Zapier
    |   |   |-- database     <- Common functions for interchangeable database. Only postgres for now.
    |   |   |-- email        <- Send or schedule send emails. Only SendGrid for now.
    |   |   |-- storage      <- Work with cloud storage buckets in AWS and GCP
    |   |
    |   |-- daos             <- Data Access Objects - simple interfaces to one or many database models
    |   |   |-- user.py      <- main DAO for common user functions
    |   |
    |   |-- db               <- sqlalchemy database models
    |       |-- models.py    <- Database models and architecture
    |
    |-- docs                 <- A default Sphinx project; see sphinx-doc.org for details
    |   |-- make             <- Builder for docs, but use the CLI build scripts for more convenience
    |
    |-- notebooks            <- Exploratory data analysis notebooks for jupyter
    |
    |-- migrations           <- Database migrations generated and managed with Alembic
    |
    |-- config.py            <- Main script for processing secrets, environment variables, and version numbers
    |
    |-- api                  <- Source code for the model server
    |   |-- __init__.py      <- Makes app a Python module. Contains the Flask app factory
    |   |
    |   |-- routes           <- API routes for the Flask API
    |   |   |-- routes.py    <- main routes for the app
    |   |   |-- auth.py      <- authentication infrastructure
    |   |
    |   |-- __init__.py      <- Flask initialization and configuration
    |   |-- requirements.txt <- Dependencies specifically for the model server
    |
    |-- host                 <- Scripts and markdown for hosting within cloud services
    |   |-- test-all.sh      <- Script for automatically running all tests and stopping at failure
    |   |-- cloudbuild       <- Compiled scripts for Google Cloud Build
    |   |-- functions        <- Cloud Functions like ETL and scheduled operations
    |
    |-- frontend             <- Simple Svelte/React frontend template
    |
    |-- tests                     <- Source code for all project tests (see Testing below)
        |-- unit_tests.py         <- Tests all app functions. >90% coverage expected.
        |
        |-- integration_tests.py  <- Tests against an instance of the model server
        |
        |-- acceptance_tests.py   <- Tests against an instance in a Staging env (see Deployment Strategy)
        |
        |-- smoke_tests.py        <- Tests against an instance in a Production env (see Deployment Strategy)


Training Notebooks
------------------

The notebooks for model training and analysis are in ./notebooks

The notebooks folder has its own requirements.txt and Dockerfile because there are a wider variety of dependencies
needed for exploratory analysis.

The notebook server can be launched using the Command-Line Interface (__run_cli) using the server menu (s)
and selecting the notebook server (n).

Usage
=====

Testing the endpoint
--------------------

Once built and running, make a GET or POST call to http://localhost:5000/ping
- Can perform this call to test using httpie:
``` bash
http --form --json POST http://localhost:5000/ping'
```
Or use Postman or requests

Deployment Strategy
===================

The goal of DevOps is to make it easy to frequently update code,
because the toolchain is automated and robust.
The codebase will also be more stable and easier to read as a side effect of deploying code becoming easier.

Dev / Testing
-------------

These are local or remote, but are focused on fast turnaround.
For example, this environment is allowed to run the Flask debug server
which auto-restarts when it detects a code change.
You can also mount the code and models as docker volumes
instead of waiting on the models to copy into the container.

Code changes should be as instantaneous as possible for fast development.

To exit dev/staging, tag and push your commit.
That will trigger the build pipeline to run unit and integration tests (see Testing below)
and promote the server to Staging.

Staging / Demo-Staging
----------------------

Staging should be the closest possible replica to Production with identical
non-prod resources and APIs.

The Staging server is used for Acceptance tests
and other non-prod performance monitoring systems.

Staging should also replicate the security constraints of Production
to ensure that they don't interfere with performance.

There are actually two staging servers in this project - staging and demo-staging. Demo-staging has only non-client
data and is used as a public-facing tool to demo the system's capabilities.

Production
----------

Production follows the strictest safety standards and may not be in the developer's control.
For now, we'll assume it isn't.

Therefore we should think of deploying to production as high-friction but low risk.
We've mitigated the risks introduced by not being able to rapidly patch the system
with a testing strategy that tries to minimize the situations that we would need to.

Testing Strategy
================

Why we test
-----------

Fast and stable pipelines are built with aggressive testing.
We use 3 kinds of tests in our CI/CD pipeline: unit, integration, and acceptance.

Unit tests are to ensure that individual "units" of code are working,
as opposed to integration and acceptance tests, which are to ensure that the code
is integrating with other resources correctly. So they can be run in isolation.
Think of them as ensuring that functions and methods are following their "contract"
that if we pass them x then they are always supposed to answer y.

Integration and acceptance tests assume that there is a server to talk to,
as well as mocks or sandboxes of other resources. Integration tests are part of the
build process, so they can be in the local environment or the build system.

Acceptance tests assume that they are talking to the Staging environment,
which should be an exact replica of production.

Smoke tests ensure that production is configured and working correctly with a few quick demo behaviors.

All tests must be passing for each new PR, and preferably each code commit. Please squash-and-merge any PRs that
include commits with test failures in them. That way, all commits represent valid, passing states for the system.

High test coverage allows us to rapidly iterate and refactor the code,
stitch all the affected tests up, and push it through the pipeline.

Tests are all run using the 'testing menu' of the command-line interface.

Unit Tests
----------

We want to make sure that the basic functions are working as expected.
Eventually the build pipeline will handle this process, and it can be part of the CI/CD pipeline.

Integration Tests
-----------------

Integration tests are for testing the API in a dev environment, either local or remote.

Acceptance Tests
----------------

Acceptance tests are for testing the API in a staging environment which exactly replicates production.

Tag and push the model to start the CI/CD pipeline. If all tests pass, the current version will be pushed to staging.

Load Testing
------------

How does the system perform under load? What is the breaking point for the app? We can answer these questions with
locust, a python library used for load testing apps. You can run a locust test against the app with:

    pip install locust
    locust -f tests/locustfile.py

Other Testing Strategies
------------------------

We may test code in other ways that don't use the normal testing tools.

Fuzzing is a form of testing where random or broken data is pushed through an input to watch for failures.

Mutation Testing makes random changes to the code base and watches what percentage of changes make it through
without tests failing. This is used to fix a code base that appears to have high test coverage but the tests
aren't very thorough.


Configuration/Secrets Strategy
==============================

Configurations and secrets need to be injected into the api and frontend in order to set them up for the different
deployment environments. The api is expecting an integration.env file and the frontend is expecting one at
client/.env.local in order to load secrets and configurations.

These files are compiled using a templating system to change the base secret file (secret--template.env),
injecting the settings for the targeted environment from (secret--template-values.env).

These two secrets are used to generate the secrets for all of the environments for the app.

Client Code names
-----------------

Because we need to adapt the SSO system to a variety of clients, we have to build different frontend apps for each
one. We need to identify what secret to get for that without storing client names in the code. So in the code,
they have animal names. Those names correspond to the entries in the secret--template-values.env file which
also shows the real client name. So they can be looked up either by that file or using the Cloud Run domains page -
https://console.cloud.google.com/run/domains?cloudshell=false&project=utility-range-256119


Troubleshooting
---------------

If a .sh script won't run in windows, open a gitforwindows or MINGW shell and update it with:


```bash
    git update-index --chmod=+x <file>
    dos2unix <file>
```

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
