#!/bin/bash
# determine_affected_services.sh

echo "::group::$(basename "$0") log" >&2
trap 'EXIT_CODE=$?; echo -n "::endgroup::" >&2; if [ $EXIT_CODE -ne 0 ]; then echo "❌ $(basename "$0") failed with exit code $EXIT_CODE!" >&2; else echo "✅ $(basename "$0") succeeded!" >&2; fi' EXIT
set -e

AFFECTED_SERVICES_ARRAY=()
ALL_SERVICES_ARRAY=()
FORCE_UPDATE_ALL=false
CHANGED_FILES_INPUT="$1" # Expecting a string of filenames, space-separated
ASSUME_POTENTIAL_VALUE_CHANGES="${2:-false}" # Default to "false" if not provided

# Populate ALL_SERVICES_ARRAY
if [ -d "services" ]; then
  ALL_SERVICES_ARRAY=($(find services -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort -u))
else
  echo "Warning: 'services' directory not found. No services to process." >&2
  echo "" >&2
  exit 0
fi

if [ ${#ALL_SERVICES_ARRAY[@]} -eq 0 ]; then
    echo "No services found in the 'services' directory." >&2
    echo "" >&2
    exit 0
fi

echo "All known services: ${ALL_SERVICES_ARRAY[@]}" >&2
echo "Changed files input: '$CHANGED_FILES_INPUT'" >&2
echo "Assume potential value changes flag: $ASSUME_POTENTIAL_VALUE_CHANGES" >&2

# Convert space-separated string of filenames to an array
IFS=' ' read -r -a CHANGED_FILES <<< "$CHANGED_FILES_INPUT"

if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
  for file in "${CHANGED_FILES[@]}"; do
    echo "Processing changed file: $file" >&2
    if [[ "$file" == services/* ]]; then
      service_name=$(echo "$file" | cut -d/ -f2)
      if [[ ! " ${AFFECTED_SERVICES_ARRAY[@]} " =~ " ${service_name} " ]]; then
        echo "Service '$service_name' affected by change in '$file'." >&2
        AFFECTED_SERVICES_ARRAY+=("$service_name")
      fi
    # Removed generate_quadlet_of_service.sh from this list. Changes to it will apply to services as they are processed.
    elif [[ "$file" == .github/workflows/scripts/add_network_names.sh || \
            "$file" == .github/workflows/scripts/add_volume_names.sh || \
            "$file" == .github/workflows/scripts/add_partof_services.sh || \
            "$file" == .github/workflows/scripts/add_oneshot_services.sh || \
            "$file" == .github/workflows/scripts/add_autoupdate_labels.sh || \
            "$file" == .github/workflows/scripts/generate_meta_services.sh || \
            "$file" == .github/workflows/scripts/generate_quadlets.sh ]]; then
      echo "Core Quadlet generation script '$file' changed. Flagging all services for update." >&2
      FORCE_UPDATE_ALL=true
      break
    elif [[ "$file" == .github/workflows/scripts/create_env_variables.sh || \
            "$file" == .github/workflows/scripts/check-env.sh || \
            "$file" == .github/workflows/scripts/check-service-envs.sh || \
            "$file" == .github/workflows/scripts/generate-env-from-gh-variables.sh || \
            "$file" == .github/workflows/scripts/add_secrets_to_env.sh || \
            "$file" == .github/workflows/scripts/refresh_podman_secrets.sh ]]; then
      echo "Environment/secret script '$file' changed. Flagging all services for update." >&2
      FORCE_UPDATE_ALL=true
      break
    elif [[ "$file" == .github/workflows/release.yml ]]; then
      echo "Release workflow file '$file' changed. Flagging all services for update (as a precaution)." >&2
      FORCE_UPDATE_ALL=true
      break
    fi
  done
else
  echo "No files reported as changed." >&2
fi

if $FORCE_UPDATE_ALL; then
  echo "FORCE_UPDATE_ALL is true (due to critical script change or explicit flag). All services will be updated." >&2
  AFFECTED_SERVICES_OUTPUT="${ALL_SERVICES_ARRAY[@]}"
elif [ ${#AFFECTED_SERVICES_ARRAY[@]} -eq 0 ] && [ "$ASSUME_POTENTIAL_VALUE_CHANGES" == "true" ]; then
  echo "No specific code changes detected, but ASSUME_POTENTIAL_VALUE_CHANGES is true. Flagging all services for update." >&2
  AFFECTED_SERVICES_OUTPUT="${ALL_SERVICES_ARRAY[@]}"
  # FORCE_UPDATE_ALL=true # Not strictly needed to set this again, as output is already all services
elif [ ${#AFFECTED_SERVICES_ARRAY[@]} -eq 0 ]; then
  echo "No specific services affected by file changes, and ASSUME_POTENTIAL_VALUE_CHANGES is false." >&2
  AFFECTED_SERVICES_OUTPUT=""
else
  echo "Specific services affected by file changes: ${AFFECTED_SERVICES_ARRAY[@]}" >&2
  AFFECTED_SERVICES_OUTPUT="${AFFECTED_SERVICES_ARRAY[@]}"
fi

echo "Final affected services string: '$AFFECTED_SERVICES_OUTPUT'" >&2
echo "$AFFECTED_SERVICES_OUTPUT"
