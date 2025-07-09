#!/bin/bash

# Deploys services on the host using the Python release tool and other host scripts.
# This script is intended to be run on the remote deployment server, typically via SSH.

set -e # Exit immediately if a command exits with a non-zero status.
set -u # Treat unset variables as an error when substituting.
set -o pipefail # Causes a pipeline to return the exit status of the last command in the pipe that returned a non-zero exit status.

# --- Helper Functions ---
# Enhanced logging and error handling functions

# Get current timestamp in ISO format
get_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Structured logging with timestamps
log_step() {
    echo ""
    echo "----------------------------------------------------------------------"
    echo "🚀 [$(get_timestamp)] STEP: $1"
    echo "----------------------------------------------------------------------"
}

log_info() {
    echo "ℹ️  [$(get_timestamp)] INFO: $1"
}

log_warning() {
    echo "⚠️  [$(get_timestamp)] WARN: $1" >&2
}

log_error() {
    echo "❌ [$(get_timestamp)] ERROR: $1" >&2
}

log_success() {
    echo "✅ [$(get_timestamp)] SUCCESS: $1"
}

# Function to validate required environment variables
validate_required_vars() {
    local required_vars=("$@")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_error "Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    return 0
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate system prerequisites
validate_prerequisites() {
    local required_commands=("podman" "git" "jq")
    local missing_commands=()
    
    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        log_error "Missing required commands: ${missing_commands[*]}"
        return 1
    fi
    
    # Check if podman is running
    if ! podman info >/dev/null 2>&1; then
        log_error "Podman is not accessible or not running"
        return 1
    fi
    
    return 0
}

# Function to perform health checks
perform_health_checks() {
    # Check disk space
    local available_space=$(df / | tail -1 | awk '{print $4}' 2>/dev/null || echo "0")
    local required_space=1048576  # 1GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        log_error "Insufficient disk space. Available: ${available_space}KB, Required: ${required_space}KB"
        return 1
    fi
    
    # Check memory
    local available_memory=$(free | grep '^Mem:' | awk '{print $7}' 2>/dev/null || echo "0")
    local required_memory=524288  # 512MB in KB
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        log_warning "Low available memory. Available: ${available_memory}KB, Recommended: ${required_memory}KB"
    fi
    
    return 0
}

# Function to retry commands with exponential backoff
retry_command() {
    local max_attempts=3
    local delay=2
    local command="$1"
    local description="${2:-Command}"
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if eval "$command" >/dev/null 2>&1; then
            return 0
        else
            local exit_code=$?
            
            if [ $attempt -lt $max_attempts ]; then
                sleep $delay
                delay=$((delay * 2))  # Exponential backoff
            else
                log_error "$description failed after $max_attempts attempts (exit code: $exit_code)"
                # Show error output only on final failure
                eval "$command"
            fi
        fi
        
        attempt=$((attempt + 1))
    done
    
    return 1
}

# Function to cleanup on exit
cleanup() {
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_success "Deployment completed successfully"
    else
        log_error "Deployment failed with exit code $exit_code"
        
        # Log system state for debugging
        log_info "System state at failure:"
        log_info "Disk usage: $(df -h / | tail -1 2>/dev/null || echo 'unknown')"
        log_info "Memory usage: $(free -h | head -2 | tail -1 2>/dev/null || echo 'unknown')"
        log_info "Running containers: $(podman ps --format '{{.Names}}' | wc -l 2>/dev/null || echo '0')"
    fi
    
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# --- Global Parameters (set from script arguments) ---
SCRIPT_AFFECTED_SERVICES="${1:-}"
SCRIPT_VARS_JSON_STR="${2:-{\}}"
SCRIPT_SECRETS_JSON_STR="${3:-{\}}"
SCRIPT_DEPLOY_SERVICES="${4:-}"

# --- Main Function ---
main() {
    log_step "Deployment Initialization"
    
    # Validate system prerequisites first
    if ! validate_prerequisites; then
        log_error "Prerequisites validation failed"
        exit 1
    fi
    
    # Perform health checks
    if ! perform_health_checks; then
        log_error "Health checks failed"
        exit 1
    fi
    
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
    # HOST_SCRIPTS_DIR determines the location of helper scripts.
    # It defaults to this script's directory but can be overridden by TEST_OVERRIDE_HOST_SCRIPTS_DIR for testing.
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
    [ -n "$SCRIPT_AFFECTED_SERVICES" ] && log_info "Affected Services: '$SCRIPT_AFFECTED_SERVICES'"
    [ -n "$SCRIPT_DEPLOY_SERVICES" ] && log_info "Deploy Services: '$SCRIPT_DEPLOY_SERVICES'"
    log_info "Project Directory: $PROJECT_DIR_ON_HOST"
    log_info "Release Tool Image: $RELEASE_TOOL_FULL_IMAGE_NAME"


# Ensure critical directories exist on the host
mkdir -p "$PROJECT_DIR_ON_HOST"
mkdir -p "$SYSTEMD_USER_UNITS_DIR_ON_HOST"
# The main repository (containing services/, .github/workflows/scripts/, etc.)
# is assumed to be already checked out or synced to $PROJECT_DIR_ON_HOST by the CI system (e.g., via ssh-action's sync).
cd "$PROJECT_DIR_ON_HOST"


log_step "Pulling Release Tool Docker Image"
if ! retry_command "podman pull '$RELEASE_TOOL_FULL_IMAGE_NAME'" "Pulling release tool image"; then
    log_error "Failed to pull release tool image: $RELEASE_TOOL_FULL_IMAGE_NAME. Deployment aborted."
    exit 1
fi


log_step "Refreshing Podman Secrets"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/refresh_podman_secrets.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    if ! retry_command "'$_SCRIPT_PATH' '$SCRIPT_SECRETS_JSON_STR'" "Refreshing podman secrets"; then
        log_error "Failed to refresh podman secrets"
        exit 1
    fi
else
    log_warning "refresh_podman_secrets.sh not found. Skipping."
fi


log_step "Creating/Updating Environment Variables File"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/create_env_variables.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    (cd "$PROJECT_DIR_ON_HOST" && "$_SCRIPT_PATH" "$SCRIPT_VARS_JSON_STR" >/dev/null 2>&1) || log_warning "Environment variables script failed"
else
    log_warning "create_env_variables.sh not found. Skipping."
fi


log_step "Sourcing Environment Files"
set -o allexport # Export all sourced variables
[ -f "$PROJECT_DIR_ON_HOST/.env" ] && source "$PROJECT_DIR_ON_HOST/.env" 2>/dev/null || log_warning ".env not found"
[ -f "$PROJECT_DIR_ON_HOST/services/version.env" ] && source "$PROJECT_DIR_ON_HOST/services/version.env" 2>/dev/null || log_warning "version.env not found"
set +o allexport


log_step "Checking Service Environment Variables"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/check-service-envs.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    "$_SCRIPT_PATH" >/dev/null 2>&1 || log_warning "Service environment check failed"
else
    log_warning "check-service-envs.sh not found. Skipping."
fi


log_step "Generating Quadlet Units (Python Tool)"
# Mounts:
# - Services definitions from host (ro)
# - Systemd user units output directory on host (rw)
# Note: Paths inside the container for the tool are fixed (e.g., /app/services, /app/output_units)
DEPLOY_SERVICES_ARG=""
if [ -n "$SCRIPT_DEPLOY_SERVICES" ]; then
    DEPLOY_SERVICES_ARG="--deploy-services $SCRIPT_DEPLOY_SERVICES"
fi

# Validate that required directories exist
if [ ! -d "$SERVICES_DEF_DIR_ON_HOST" ]; then
    log_error "Services definition directory does not exist: $SERVICES_DEF_DIR_ON_HOST"
    exit 1
fi

QUADLET_COMMAND="podman run --rm \
    --security-opt label=disable \
    -v '$SERVICES_DEF_DIR_ON_HOST:/app/services:ro,Z' \
    -v '$SYSTEMD_USER_UNITS_DIR_ON_HOST:/app/output_units:rw,Z' \
    '$RELEASE_TOOL_FULL_IMAGE_NAME' generate-units \
    --affected-services '$SCRIPT_AFFECTED_SERVICES' \
    --services-dir '/app/services' \
    --output-dir '/app/output_units' \
    --meta-target 'all-containers.target' \
    --vars-json '$SCRIPT_VARS_JSON_STR' \
    $DEPLOY_SERVICES_ARG"

if ! retry_command "$QUADLET_COMMAND" "Generating quadlet units"; then
    log_error "Failed to generate quadlet units"
    exit 1
fi


log_step "Running Quadlet Dry Run"
if [ -x "$QUADLET_EXEC" ]; then
    "$QUADLET_EXEC" --dryrun --user --no-header "$SYSTEMD_USER_UNITS_DIR_ON_HOST" >/dev/null 2>&1 || log_warning "Quadlet dry run failed"
else
    log_warning "Quadlet not found. Skipping dry run."
fi


log_step "Generating Meta Services"
_SCRIPT_PATH="$HOST_SCRIPTS_DIR/generate_meta_services.sh"
if [ -f "$_SCRIPT_PATH" ]; then
    "$_SCRIPT_PATH" >/dev/null 2>&1 || log_warning "Meta services generation failed"
else
    log_warning "generate_meta_services.sh not found. Skipping."
fi


log_step "Pulling Container Images (Python Tool)"
# Mounts:
# - Podman socket for the tool to run `podman pull`
# - Systemd user units directory (ro) for the tool to read .container files

# Validate podman socket exists
if [ ! -S "$PODMAN_SOCKET" ]; then
    log_error "Podman socket not found: $PODMAN_SOCKET"
    exit 1
fi

PULL_COMMAND="podman run --rm \
    --security-opt label=disable \
    -v '$PODMAN_SOCKET:/var/run/podman/podman.sock:Z' \
    -v '$SYSTEMD_USER_UNITS_DIR_ON_HOST:/app/units:ro,Z' \
    '$RELEASE_TOOL_FULL_IMAGE_NAME' pull-images \
    --affected-services '$SCRIPT_AFFECTED_SERVICES' \
    --units-dir '/app/units'"

if ! retry_command "$PULL_COMMAND" "Pulling container images"; then
    log_error "Failed to pull container images"
    exit 1
fi


log_step "Restarting Services (Python Tool)"
# Mounts:
# - Podman socket (potentially, though systemctl might not need it if just restarting existing)
# - Systemd user bus socket for the tool to run `systemctl --user` commands

# Validate systemd user bus socket exists
if [ ! -S "$SYSTEMD_USER_BUS_SOCKET" ]; then
    log_error "Systemd user bus socket not found: $SYSTEMD_USER_BUS_SOCKET"
    exit 1
fi

RESTART_COMMAND="podman run --rm \
    --security-opt label=disable \
    -v '$PODMAN_SOCKET:/var/run/podman/podman.sock:Z' \
    -v '$SYSTEMD_USER_BUS_SOCKET:/run/systemd/user/bus:Z' \
    '$RELEASE_TOOL_FULL_IMAGE_NAME' manage-services restart \
    --affected-services '$SCRIPT_AFFECTED_SERVICES'"

if ! retry_command "$RESTART_COMMAND" "Restarting services"; then
    log_error "Failed to restart services"
    exit 1
fi


log_step "Triggering Podman Auto-Update"
if ! retry_command "podman auto-update" "Podman auto-update"; then
    log_warning "Podman auto-update failed or found no updates, continuing..."
fi

log_step "Post-Deployment Validation"
# Validate that affected services are running
if [ -n "$SCRIPT_AFFECTED_SERVICES" ]; then
    # Wait for services to stabilize
    sleep 10
    
    # Check service status
    IFS=' ' read -r -a services_array <<< "$SCRIPT_AFFECTED_SERVICES"
    failed_services=()
    
    for service in "${services_array[@]}"; do
        if ! systemctl --user is-active "$service" >/dev/null 2>&1; then
            log_error "Service $service is not running"
            failed_services+=("$service")
        fi
    done
    
    if [ ${#failed_services[@]} -gt 0 ]; then
        log_error "The following services failed to start: ${failed_services[*]}"
        
        # Log service status for debugging
        for service in "${failed_services[@]}"; do
            log_info "Status for $service:"
            systemctl --user status "$service" || true
        done
        
        exit 1
    fi
fi

# Final system health check
log_info "Active containers: $(podman ps --format '{{.Names}}' | wc -l 2>/dev/null || echo '0')"
log_info "Available disk space: $(df -h / | tail -1 | awk '{print $4}' 2>/dev/null || echo 'unknown')"

log_step "Deployment Script Finished Successfully"
    # exit 0 # Implicit exit 0 if no errors due to set -e
}

# --- Script Entry Point ---
main "$@"
