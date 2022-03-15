#!/bin/bash
readonly function="$1"
# Stage is the build environment (dev, staging, prod, ...)
readonly stage="$2"
readonly entrypoint="$3"

gcloud functions deploy "$function-$stage" \
     --region=us-central1 \
     --source=./etl \
     --entry-point="$entrypoint"
