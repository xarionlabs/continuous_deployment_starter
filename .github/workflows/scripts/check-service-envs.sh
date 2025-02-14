#!/bin/bash
echo "::group::$(basename "$0") log"
set -e
trap 'EXIT_CODE=$?; echo -n "::endgroup::"; if [ $EXIT_CODE -ne 0 ]; then echo "❌ $(basename "$0") failed!"; else echo "✅ $(basename "$0") succeeded!"; fi' EXIT
missing_any=0

if [[ ! -d "services" ]]; then
    echo "Error: 'services' directory not found!"
    exit 1
fi

for service in services/*; do
  if [[ -d "$service" ]]; then
    compose_files=("$service/"*compose.y*ml)

    if [[ ! -f "${compose_files[0]}" ]]; then
        echo "Warning: No compose file found in $service, skipping..."
        continue
    fi

    for compose_file in "${compose_files[@]}"; do
        echo "Checking environment variables for: $compose_file"
        check-env.sh "$compose_file" || missing_any=1
    done
  fi
done
echo "::endgroup::"
if [[ "$missing_any" -eq 1 ]]; then
    echo "❌ Missing environment variables detected. Please check the output above.\n
    Make sure that your Github environment has these variables set. "
    exit 1
else
    echo "✅ All services have required environment variables set!"
fi
