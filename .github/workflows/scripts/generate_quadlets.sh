#!/bin/bash
echo "::group::$(basename "$0") log"
trap 'EXIT_CODE=$?; echo -n "::endgroup::"; if [ $EXIT_CODE -ne 0 ]; then echo "❌ $(basename "$0") failed with exit code $EXIT_CODE!"; else echo "✅ $(basename "$0") succeeded!"; fi' EXIT
set -e # Exit immediately if a command exits with a non-zero status.

AFFECTED_SERVICES_STRING="$1"
CONFIG_DIR="$HOME/.config/containers/systemd"

# Convert space-separated string of service names to an array
IFS=' ' read -r -a AFFECTED_SERVICES <<< "$AFFECTED_SERVICES_STRING"

if [ ${#AFFECTED_SERVICES[@]} -eq 0 ]; then
  echo "No services passed as affected. Skipping Quadlet generation."
  # The helper scripts below might still be needed if they perform global setup
  # or if this script is ever called when AFFECTED_SERVICES is empty but some global
  # change (not service-specific) occurred that needs these helpers to run.
  # For now, we'll let them run as they might have their own idempotency.
  # Consider adding a flag if truly nothing should happen.
else
  echo "Affected services for Quadlet generation: ${AFFECTED_SERVICES[@]}"

  # Ensure the systemd directory for containers exists
  mkdir -p "$CONFIG_DIR"

  echo "Cleaning up existing Quadlet files for affected services..."
  for service_name in "${AFFECTED_SERVICES[@]}"; do
    echo "Removing existing files for service: $service_name (if any)"
    # Remove .service, .container, .volume, .network files associated with this service name
    rm -f "$CONFIG_DIR/$service_name".*
  done

  echo "Generating Quadlet files for affected services..."
  for service_name in "${AFFECTED_SERVICES[@]}"; do
    service_dir="services/$service_name"
    if [[ -d "$service_dir" ]]; then
      # Check for compose files within the specific service directory
      # Using a subshell to find files and check allows for cleaner error handling if no files found
      compose_file_found=$(find "$service_dir" -maxdepth 1 -name '*compose.y*ml' -print -quit)

      if [[ -n "$compose_file_found" ]]; then
        echo "Generating Quadlet for service: $service_name from $service_dir"
        (cd "$service_dir" && generate_quadlet_of_service.sh "$service_name")
      else
        echo "No compose file found for service $service_name in $service_dir. Skipping Quadlet generation for it."
      fi
    else
      echo "Service directory $service_dir not found for affected service $service_name. Skipping."
    fi
  done
fi

# These helper scripts might operate globally or on all generated files.
# Their internal logic would need to be made selective if desired.
# For now, they run after any affected services have had their quadlets (re)generated.
echo "Running helper scripts for Quadlet enhancement..."
add_network_names.sh
add_volume_names.sh
add_partof_services.sh
add_secrets_to_env.sh
add_oneshot_services.sh
add_autoupdate_labels.sh

echo "Quadlet generation process complete."
echo "::endgroup::"