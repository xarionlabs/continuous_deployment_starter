#!/bin/bash

# Deploys services on the host using the Python release tool and other host scripts.
# This script is intended to be run on the remote deployment server, typically via SSH.

set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error when substituting.
set -o pipefail # Causes a pipeline to return the exit status of the last command in the pipe that returned a non-zero exit status.

# --- Helper Functions ---
# It's good practice to define functions before they are called, especially with `set -u`.
log_step() {
    echo ""
    echo "----------------------------------------------------------------------"
    echo "🚀 STEP: $1"
    echo "----------------------------------------------------------------------"
}

log_info() {
    echo "INFO: $1"
}

log_warning() {
    echo "WARN: $1" >&2
}

log_error() {
    echo "ERROR: $1" >&2
}

# --- Global Parameters (set from script arguments) ---
SCRIPT_AFFECTED_SERVICES="${1:-}"
SCRIPT_VARS_JSON_STR="${2:-{\}}"
SCRIPT_SECRETS_JSON_STR="${3:-{\}}"

# --- Main Function ---
main() {
    # Use script-global variables for parameters

    # --- Configuration (adjust these paths if your remote setup differs) ---
    REMOTE_USER_HOME_REAL=$(eval echo "~$USER") # Actual home dir of the user running the script
    PROJECT_DIR_ON_HOST_DEFAULT="$REMOTE_USER_HOME_REAL/runtime/continuous_deployment_starter"
    # Default location for other scripts is now relative to this script itself
    HOST_SCRIPTS_DIR_DEFAULT="$(dirname "$0")"
    SERVICES_DEF_DIR_ON_HOST_DEFAULT="$PROJECT_DIR_ON_HOST_DEFAULT/services" # This remains based on project root
    SYSTEMD_USER_UNITS_DIR_ON_HOST_DEFAULT="$REMOTE_USER_HOME_REAL/.config/containers/systemd"
    QUADLET_EXEC_DEFAULT="/usr/libexec/podman/quadlet"

    # Allow overriding paths for testing
    PROJECT_DIR_ON_HOST="${TEST_OVERRIDE_PROJECT_DIR_ON_HOST:-$PROJECT_DIR_ON_HOST_DEFAULT}"
    SERVICES_DEF_DIR_ON_HOST="${TEST_OVERRIDE_SERVICES_DEF_DIR:-$SERVICES_DEF_DIR_ON_HOST_DEFAULT}"
    # HOST_SCRIPTS_DIR is now primarily where this script itself resides, and other scripts are called relative to it.
    # The TEST_OVERRIDE_HOST_SCRIPTS_DIR can still be used by tests to place mock scripts if needed,
    # but the script's internal calls will use `$(dirname "$0")/script.sh`.
    HOST_SCRIPTS_DIR="${TEST_OVERRIDE_HOST_SCRIPTS_DIR:-$(dirname "$0")}"
    SYSTEMD_USER_UNITS_DIR_ON_HOST="${TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR:-$SYSTEMD_USER_UNITS_DIR_ON_HOST_DEFAULT}"
    QUADLET_EXEC="${TEST_OVERRIDE_QUADLET_PATH:-$QUADLET_EXEC_DEFAULT}"


    # Podman and Systemd socket paths (usually standard for rootless Podman)
    # These are less likely to be overridden in tests unless mocking podman socket interactions.
    PODMAN_SOCKET="${TEST_OVERRIDE_PODMAN_SOCKET:-/run/user/$(id -u)/podman/podman.sock}"
    SYSTEMD_USER_BUS_SOCKET="/run/user/$(id -u)/bus"

    # Release Tool Docker Image (ensure this matches what your CI builds and pushes)
    # Using GITHUB_REPOSITORY_OWNER is a placeholder; replace with your actual org/user if needed,
    # or pass this as a parameter if it changes frequently.
    RELEASE_TOOL_IMAGE_OWNER="${GITHUB_REPOSITORY_OWNER:-your_ghcr_io_user_or_org}" # Fallback for local testing
    RELEASE_TOOL_IMAGE_REPO_NAME="continuous_deployment_starter" # Assuming this is the repo name, could also be dynamic from GITHUB_REPOSITORY
    RELEASE_TOOL_IMAGE_NAME="release-tool"
    RELEASE_TOOL_IMAGE_TAG="latest" # Default tag

    # Use PYTHON_RELEASE_TOOL_IMAGE if set (passed from GHA), otherwise construct it
    if [ -n "${PYTHON_RELEASE_TOOL_IMAGE:-}" ]; then
        RELEASE_TOOL_FULL_IMAGE_NAME="$PYTHON_RELEASE_TOOL_IMAGE"
        log_info "Using release tool image from PYTHON_RELEASE_TOOL_IMAGE env var: $RELEASE_TOOL_FULL_IMAGE_NAME"
    else
        # Construct with GITHUB_REPOSITORY_OWNER if PYTHON_RELEASE_TOOL_IMAGE is not set
        # This part might need adjustment if GITHUB_REPOSITORY_OWNER is not reliably available or correct in all execution contexts of this script
        RELEASE_TOOL_FULL_IMAGE_NAME="ghcr.io/$RELEASE_TOOL_IMAGE_OWNER/${RELEASE_TOOL_IMAGE_REPO_NAME#*/}/$RELEASE_TOOL_IMAGE_NAME:$RELEASE_TOOL_IMAGE_TAG"
        # The ${RELEASE_TOOL_IMAGE_REPO_NAME#*/} is to get only the repo name if GITHUB_REPOSITORY was passed as owner/repo
        log_info "PYTHON_RELEASE_TOOL_IMAGE not set. Constructing image name: $RELEASE_TOOL_FULL_IMAGE_NAME"
    fi

    log_step "Initializing Deployment on Host"
    log_info "Affected Services: '$SCRIPT_AFFECTED_SERVICES'" # Use global var
log_info "Project Directory on Host: $PROJECT_DIR_ON_HOST"
log_info "Services Definitions on Host: $SERVICES_DEF_DIR_ON_HOST"
log_info "Systemd User Units Directory on Host: $SYSTEMD_USER_UNITS_DIR_ON_HOST"
log_info "Release Tool Image: $RELEASE_TOOL_FULL_IMAGE_NAME"
# Avoid logging full VARS_JSON_STR and SECRETS_JSON_STR for security, just acknowledge receipt
    log_info "VARS_JSON_STR received: $(if [ -z "$SCRIPT_VARS_JSON_STR" ] || [ "$SCRIPT_VARS_JSON_STR" == "{}" ]; then echo "false"; else echo "true"; fi)" # Use global var
    log_info "SECRETS_JSON_STR received: $(if [ -z "$SCRIPT_SECRETS_JSON_STR" ] || [ "$SCRIPT_SECRETS_JSON_STR" == "{}" ]; then echo "false"; else echo "true"; fi)" # Use global var


# Ensure critical directories exist on the host
mkdir -p "$PROJECT_DIR_ON_HOST"
mkdir -p "$SYSTEMD_USER_UNITS_DIR_ON_HOST"
# The main repository (containing services/, .github/workflows/scripts/, etc.)
# is assumed to be already checked out or synced to $PROJECT_DIR_ON_HOST by the CI system (e.g., via ssh-action's sync).
cd "$PROJECT_DIR_ON_HOST"


log_step "Pulling Release Tool Docker Image"
if ! podman pull "$RELEASE_TOOL_FULL_IMAGE_NAME"; then
    log_error "Failed to pull release tool image: $RELEASE_TOOL_FULL_IMAGE_NAME. Deployment aborted."
    exit 1
fi
log_info "Successfully pulled $RELEASE_TOOL_FULL_IMAGE_NAME."


log_step "Refreshing Podman Secrets (Host Script)"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/refresh_podman_secrets.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    "$_SCRIPT_PATH" "$SECRETS_JSON_STR"
else
    log_warning "refresh_podman_secrets.sh not found at $_SCRIPT_PATH. Skipping."
fi


log_step "Creating/Updating Environment Variables File (Host Script)"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/create_env_variables.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    # This script is assumed to create/update .env in $PROJECT_DIR_ON_HOST
    # It might need VARS_JSON_STR if it's designed to consume it directly.
    # For now, assuming it handles sourcing variables or uses a predefined GHA var file.
    # VARS_JSON_STR is available globally in this script if create_env_variables.sh needs it as an argument.
    (cd "$PROJECT_DIR_ON_HOST" && "$_SCRIPT_PATH" "$SCRIPT_VARS_JSON_STR")
else
    log_warning "create_env_variables.sh not found at $_SCRIPT_PATH. Skipping."
fi


log_step "Sourcing Environment Files"
set -o allexport # Export all sourced variables
if [ -f "$PROJECT_DIR_ON_HOST/.env" ]; then
    log_info "Sourcing $PROJECT_DIR_ON_HOST/.env"
    source "$PROJECT_DIR_ON_HOST/.env"
else
    log_warning "$PROJECT_DIR_ON_HOST/.env not found."
fi
if [ -f "$PROJECT_DIR_ON_HOST/services/version.env" ]; then
    log_info "Sourcing $PROJECT_DIR_ON_HOST/services/version.env"
    source "$PROJECT_DIR_ON_HOST/services/version.env"
else
    log_warning "$PROJECT_DIR_ON_HOST/services/version.env not found."
fi
set +o allexport


log_step "Checking Service Environment Variables (Host Script)"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/check-service-envs.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    "$_SCRIPT_PATH"
else
    log_warning "check-service-envs.sh not found at $_SCRIPT_PATH. Skipping."
fi


log_step "Generating Quadlet Units (Python Tool)"
# Mounts:
# - Services definitions from host (ro)
# - Systemd user units output directory on host (rw)
# Note: Paths inside the container for the tool are fixed (e.g., /app/services, /app/output_units)
podman run --rm \
    --security-opt label=disable \
    -v "$SERVICES_DEF_DIR_ON_HOST:/app/services:ro,Z" \
    -v "$SYSTEMD_USER_UNITS_DIR_ON_HOST:/app/output_units:rw,Z" \
    "$RELEASE_TOOL_FULL_IMAGE_NAME" generate-units \
    --affected-services "$SCRIPT_AFFECTED_SERVICES" \
    --services-dir "/app/services" \
    --output-dir "/app/output_units" \
    --meta-target "all-containers.target" \
    --vars-json "$SCRIPT_VARS_JSON_STR"
log_info "Quadlet unit generation attempt complete."


log_step "Running Quadlet Dry Run (Host Command)"
if [ -x "$QUADLET_EXEC" ]; then
    "$QUADLET_EXEC" --dryrun --user --no-header "$SYSTEMD_USER_UNITS_DIR_ON_HOST"
else
    log_warning "$QUADLET_EXEC not found. Skipping dry run."
fi


log_step "Generating Meta Services (e.g., all-containers.target) (Host Script)"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/generate_meta_services.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    "$_SCRIPT_PATH"
else
    log_warning "generate_meta_services.sh not found at $_SCRIPT_PATH. Skipping."
fi


log_step "Pulling Container Images (Python Tool)"
# Mounts:
# - Podman socket for the tool to run `podman pull`
# - Systemd user units directory (ro) for the tool to read .container files
podman run --rm \
    --security-opt label=disable \
    -v "$PODMAN_SOCKET:/var/run/podman/podman.sock:Z" \
    -v "$SYSTEMD_USER_UNITS_DIR_ON_HOST:/app/units:ro,Z" \
    "$RELEASE_TOOL_FULL_IMAGE_NAME" pull-images \
    --affected-services "$SCRIPT_AFFECTED_SERVICES" \
    --units-dir "/app/units"
log_info "Image pulling attempt complete."


log_step "Restarting Services (Python Tool)"
# Mounts:
# - Podman socket (potentially, though systemctl might not need it if just restarting existing)
# - Systemd user bus socket for the tool to run `systemctl --user` commands
podman run --rm \
    --security-opt label=disable \
    -v "$PODMAN_SOCKET:/var/run/podman/podman.sock:Z" \
    -v "$SYSTEMD_USER_BUS_SOCKET:/run/systemd/user/bus:Z" \
    "$RELEASE_TOOL_FULL_IMAGE_NAME" manage-services restart \
    --affected-services "$SCRIPT_AFFECTED_SERVICES"
log_info "Service restart attempt complete."


log_step "Triggering Podman Auto-Update (Host Command)"
podman auto-update || log_warning "Podman auto-update command failed or found no updates, continuing..."


log_step "Deployment Script Finished Successfully"
    # exit 0 # Implicit exit 0 if no errors due to set -e
}

# --- Script Entry Point ---
main "$@"
