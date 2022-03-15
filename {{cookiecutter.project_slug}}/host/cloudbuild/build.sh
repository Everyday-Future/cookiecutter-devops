#!/bin/bash
readonly service="$1"
readonly project_id="$2"
readonly tag_name="$3"
# Check for cached image or build from scratch
if docker pull gcr.io/"$project_id"/"$service":latest; then
  # Build using the cached image
  docker build . -t "gcr.io/$project_id/$service:latest" -t "$service" -t "workspace_${service}_1" --target "$service" --cache-from "gcr.io/$project_id/$service:latest"
else
  # Build without using the cache
  docker build . -t "gcr.io/$project_id/$service:latest" -t "$service" -t "workspace_${service}_1" --target "$service"
fi
# Push the tagged build
docker tag "gcr.io/$project_id/$service:latest" "gcr.io/$project_id/$service:$tag_name"
# Push the new build
docker push "gcr.io/$project_id/$service:latest"
# Push the new build
docker push "gcr.io/$project_id/$service:$tag_name"