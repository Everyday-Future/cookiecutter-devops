#!/bin/bash

python -m venv venv
venv/Scripts/pip install -r core/requirements.txt
venv/Scripts/pip install -r api/requirements.txt
venv/Scripts/python secret_builder.py local
