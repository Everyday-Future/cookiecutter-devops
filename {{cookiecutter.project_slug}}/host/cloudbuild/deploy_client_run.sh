#!/bin/bash
readonly service="$1"
# Stage is the build environment (dev, staging, prod, ...)
readonly stage="$2"
readonly project_id="$3"
readonly tag_name="$4"

gcloud run deploy "$service-$stage" \
    --image "gcr.io/$project_id/$service:$tag_name" \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated
