#!/bin/bash
readonly service="$1"
readonly new_tag="$2"
readonly project_id="$3"
readonly tag_name="$4"
# Push the tagged build
docker tag "gcr.io/$project_id/$service:$tag_name" "gcr.io/$project_id/$service:$new_tag"
# Push the new build
docker push "gcr.io/$project_id/$service:$new_tag"