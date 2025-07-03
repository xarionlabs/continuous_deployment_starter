#!/bin/bash
echo "::group::$(basename "$0") log"
trap 'EXIT_CODE=$?; echo -n "::endgroup::"; if [ $EXIT_CODE -ne 0 ]; then echo "❌ $(basename "$0") failed with exit code $EXIT_CODE!"; else echo "✅ $(basename "$0") succeeded!"; fi' EXIT
set -e # Exit immediately if a command exits with a non-zero status.

AFFECTED_SERVICES_STRING="$1"
CONFIG_DIR="$HOME/.config/containers/systemd"

# Convert space-separated string of service names to an array
IFS=' ' read -r -a AFFECTED_SERVICES <<< "$AFFECTED_SERVICES_STRING"

if [ ${#AFFECTED_SERVICES[@]} -eq 0 ]; then
  echo "No services passed as affected. Skipping image pulling."
  exit 0
fi

echo "Affected services for image pulling: ${AFFECTED_SERVICES[@]}"

if [ ! -d "$CONFIG_DIR" ]; then
  echo "Error: Configuration directory $CONFIG_DIR does not exist. Cannot pull images."
  exit 1
fi

cd "$CONFIG_DIR" || exit 1 # cd into config_dir to easily find .container files

for service_name in "${AFFECTED_SERVICES[@]}"; do
  container_file="$service_name.container"
  if [[ -f "$container_file" ]]; then
    if grep -q '^Image=' "$container_file"; then
      image=$(grep '^Image=' "$container_file" | cut -d'=' -f2)
      echo "Pulling image '$image' for service '$service_name'..."
      if ! podman pull "$image"; then
        # Log a warning but continue, as per original script's behavior
        echo "⚠️  Failed to pull $image for service $service_name - continuing with existing image if available."
      else
        echo "✅ Successfully pulled $image for service $service_name."
      fi
    else
      echo "No 'Image=' line found in $container_file for service $service_name. Skipping image pull for it."
    fi
  else
    echo "Warning: Container file $container_file not found for affected service $service_name. Skipping image pull."
  fi
done

cd - > /dev/null # Return to original directory
echo "Image pulling process complete for affected services."
echo "::endgroup::"