#!/bin/bash

for service in $(find services -mindepth 1 -maxdepth 1 -type d | sort -r); do
  if [[ -d "$service" ]]; then
    compose_files=("$service/"*compose.y*ml)

    # Check if there are any matching files (avoid running if glob didn't match)
    if [[ -e "${compose_files[0]}" ]]; then
      (cd "$service" && generate_quadlet_of_service.sh "$(basename "$service")")
    fi
  fi
done

add_network_names.sh
add_volume_names.sh
