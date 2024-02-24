#!/bin/bash
export LOAD_DOTENV=True
export SERVER_MODE=host
while true
do
	venv\Scripts\python -B cli.py
done
