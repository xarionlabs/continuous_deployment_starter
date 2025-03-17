#!/bin/bash

(echo "name: $1"; podman compose -f docker-compose.yml config) | \
  podman run \
    -i \
    --rm \
    -v ~/.config/containers/systemd:/app/systemd \
      ghcr.io/containers/podlet \
      --file /app/systemd \
      --overwrite \
      compose \
      -

find . -type f ! -name 'docker-compose.yml' -exec cp {} ~/.config/containers/systemd \;