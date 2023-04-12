# !/usr/bin/env python

import setuptools
from config import Config

setuptools.setup(
    name='{{ cookiecutter.project_slug }}',
    packages=setuptools.find_packages(),
    version=Config.VERSION,
    description='{{ cookiecutter.project_short_description }}',
    long_description='{{ cookiecutter.project_short_description }}',
    author='{{ cookiecutter.full_name }}',
    license='',
    author_email='{{ cookiecutter.email }}',
    url='https://{{ cookiecutter.project_domain }}',
    keywords=['flask', 'etl', 'docker', 'svelte'],
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Software Development',
    ],
)
