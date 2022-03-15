#!/bin/bash
export LOAD_DOTENV=True
export SERVER_MODE=host
while true
do
	python -B cli.py
done
