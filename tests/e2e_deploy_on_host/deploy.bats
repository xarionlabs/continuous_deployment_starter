#!/usr/bin/env bats

# End-to-end tests for deploy_on_host.sh
# This requires Bats-core to be installed and in PATH.

# --- Test Setup ---

# Variables to store mock call data
declare -A mock_calls # Associative array to store calls to mocks

setup() {
    # Create a temporary directory for mocks and test artifacts
    BATS_TMP_DIR=$(mktemp -d -t bats_deploy_test_XXXXXX)
    export BATS_TMP_DIR

    # Mock directory for host scripts that deploy_on_host.sh calls
    MOCK_HOST_SCRIPTS_DIR="$BATS_TMP_DIR/mock_host_scripts"
    mkdir -p "$MOCK_HOST_SCRIPTS_DIR"
    export MOCK_HOST_SCRIPTS_DIR

    # Mock directory for service definitions that deploy_on_host.sh makes available to the tool
    MOCK_SERVICES_DEF_DIR="$BATS_TMP_DIR/mock_services_definitions"
    mkdir -p "$MOCK_SERVICES_DEF_DIR"
    export MOCK_SERVICES_DEF_DIR

    # Mock directory for systemd user units output
    MOCK_SYSTEMD_USER_UNITS_DIR="$BATS_TMP_DIR/mock_systemd_units"
    mkdir -p "$MOCK_SYSTEMD_USER_UNITS_DIR"
    export MOCK_SYSTEMD_USER_UNITS_DIR

    # Path to the actual script being tested
    # Assuming it's in .github/workflows/scripts/ relative to project root
    # Bats runs tests from the directory containing the .bats file.
    # Adjust this path based on where this test file is relative to the project root.
    # For this example, assume tests/e2e_deploy_on_host/ is at root.
    # So, ../.github/workflows/scripts/deploy_on_host.sh
    SCRIPT_UNDER_TEST="$(cd "$(dirname "$BATS_TEST_FILENAME")/../" && pwd)/.github/workflows/scripts/deploy_on_host.sh"
    if [ ! -f "$SCRIPT_UNDER_TEST" ]; then
        echo "ERROR: Script under test not found at $SCRIPT_UNDER_TEST" >&2
        exit 1
    fi

    # --- Mock Implementations ---

    # Mock for 'podman' command
    cat > "$BATS_TMP_DIR/podman" <<-'EOF'
#!/bin/bash
echo "MOCK_PODMAN_CALLED: $@" >> "$BATS_TMP_DIR/podman_calls.log"
# Simulate specific behaviors based on args
if [ "$1" == "pull" ]; then
    echo "Mock Podman: Simulating pull for $2..."
    # Simulate success by default, can be overridden by test case
    if [[ "$2" == *"failpull"* ]]; then exit 1; else exit 0; fi
elif [ "$1" == "run" ]; then
    echo "Mock Podman: Simulating run with args: $@"
    # Simulate success by default for Python tool calls
    # A more advanced mock could check the release-tool command and its args
    exit 0
elif [ "$1" == "auto-update" ]; then
    echo "Mock Podman: Simulating auto-update"
    exit 0
fi
exit 0 # Default success for other podman commands
EOF
    chmod +x "$BATS_TMP_DIR/podman"

    # Mock for host scripts (refresh_podman_secrets.sh, create_env_variables.sh, etc.)
    create_mock_host_script() {
        local script_name="$1"
        cat > "$MOCK_HOST_SCRIPTS_DIR/$script_name" <<-EOF
#!/bin/bash
echo "MOCK_SCRIPT_CALLED: $script_name $@" >> "$BATS_TMP_DIR/host_script_calls.log"
exit 0 # Default success
EOF
        chmod +x "$MOCK_HOST_SCRIPTS_DIR/$script_name"
    }
    create_mock_host_script "refresh_podman_secrets.sh"
    create_mock_host_script "create_env_variables.sh"
    create_mock_host_script "check-service-envs.sh"
    create_mock_host_script "generate_meta_services.sh"

    # Mock for quadlet
    MOCK_QUADLET_DIR=$(dirname "/usr/libexec/podman/quadlet") # Should be /usr/libexec/podman
    mkdir -p "$BATS_TMP_DIR$MOCK_QUADLET_DIR"
    cat > "$BATS_TMP_DIR/usr/libexec/podman/quadlet" <<-'EOF'
#!/bin/bash
echo "MOCK_QUADLET_CALLED: $@" >> "$BATS_TMP_DIR/quadlet_calls.log"
exit 0
EOF
    chmod +x "$BATS_TMP_DIR/usr/libexec/podman/quadlet"


    # Add mocks to the PATH
    export PATH="$BATS_TMP_DIR:$MOCK_HOST_SCRIPTS_DIR:$BATS_TMP_DIR/usr/libexec/podman:$PATH"

    # Clear log files for calls
    rm -f "$BATS_TMP_DIR/podman_calls.log" "$BATS_TMP_DIR/host_script_calls.log" "$BATS_TMP_DIR/quadlet_calls.log"

    # Environment variables that deploy_on_host.sh might use or pass through
    export GITHUB_REPOSITORY_OWNER="test-owner" # For RELEASE_TOOL_IMAGE construction
    # For deploy_on_host.sh internal path definitions:
    export USER="$(whoami)" # Ensure USER is set for home dir expansion
    # The deploy_on_host.sh script uses REMOTE_USER_HOME=$(eval echo "~$USER")
    # We also need to ensure PROJECT_DIR_ON_HOST is set up correctly relative to how the script calculates it,
    # or override it for the test.
    # For tests, we'll make PROJECT_DIR_ON_HOST point to a controlled temp location.
    export PROJECT_DIR_ON_HOST="$BATS_TMP_DIR/mock_project_on_host"
    mkdir -p "$PROJECT_DIR_ON_HOST/.github/workflows/scripts" # where deploy_on_host expects to find other scripts
    mkdir -p "$PROJECT_DIR_ON_HOST/services"
    # Copy the mock host scripts into the mock project's script dir as deploy_on_host.sh expects them there
    cp "$MOCK_HOST_SCRIPTS_DIR/"* "$PROJECT_DIR_ON_HOST/.github/workflows/scripts/"

    # Redefine paths within deploy_on_host.sh for testing, if possible, or ensure mocks are in expected locations.
    # The script uses HOST_SCRIPTS_DIR="$PROJECT_DIR_ON_HOST/.github/workflows/scripts"
    # And SERVICES_DEF_DIR_ON_HOST="$PROJECT_DIR_ON_HOST/services"
    # And SYSTEMD_USER_UNITS_DIR_ON_HOST points to our mock dir
    # The key is that the script under test needs to find its dependencies (other bash scripts, python tool via mocked podman)
    # in locations it expects, or the test needs to override those locations.

    # Override SYSTEMD_USER_UNITS_DIR_ON_HOST for the script execution if it's hardcoded
    # This is tricky if the script itself defines it.
    # For now, we rely on deploy_on_host.sh using $REMOTE_USER_HOME/.config/...
    # We can create this path within BATS_TMP_DIR if needed and point REMOTE_USER_HOME there.
    # A better way: modify deploy_on_host.sh to allow overriding these paths via ENV VARS for testing.
    # For now, the mock systemd dir is $MOCK_SYSTEMD_USER_UNITS_DIR
    # The script calculates SYSTEMD_USER_UNITS_DIR_ON_HOST=$REMOTE_USER_HOME/.config/containers/systemd
    # So, we need to make REMOTE_USER_HOME point to something that makes this resolve to MOCK_SYSTEMD_USER_UNITS_DIR

    # Let's create a fake home for the test environment
    FAKE_HOME="$BATS_TMP_DIR/fake_home"
    mkdir -p "$FAKE_HOME/.config/containers/systemd"
    export HOME="$FAKE_HOME" # This will affect how ~$USER expands if USER is not root
                             # And how deploy_on_host.sh calculates REMOTE_USER_HOME and SYSTEMD_USER_UNITS_DIR_ON_HOST
                             # The script uses REMOTE_USER_HOME=$(eval echo "~$USER")
                             # For consistency, let's ensure SYSTEMD_USER_UNITS_DIR_ON_HOST in the script
                             # resolves to our MOCK_SYSTEMD_USER_UNITS_DIR.
                             # We can achieve this if deploy_on_host.sh allows overriding SYSTEMD_USER_UNITS_DIR_ON_HOST via env var.
                             # Assuming we modify deploy_on_host.sh:
    export TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR="$MOCK_SYSTEMD_USER_UNITS_DIR"
    export TEST_OVERRIDE_SERVICES_DEF_DIR="$MOCK_SERVICES_DEF_DIR"

}

teardown() {
    # Clean up temporary directory
    if [ -n "${BATS_TMP_DIR:-}" ] && [ -d "${BATS_TMP_DIR}" ]; then
        rm -rf "$BATS_TMP_DIR"
    fi
    unset BATS_TMP_DIR MOCK_HOST_SCRIPTS_DIR MOCK_SERVICES_DEF_DIR MOCK_SYSTEMD_USER_UNITS_DIR
    unset SCRIPT_UNDER_TEST
    unset PROJECT_DIR_ON_HOST
    unset TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR TEST_OVERRIDE_SERVICES_DEF_DIR
    # Restore original PATH? Bats might handle this.
}

# --- Test Cases ---

@test "deploy_on_host.sh: basic run with no affected services" {
    # Setup:
    # - Mock podman pull to succeed.
    # - Mock host scripts to succeed.
    # - Pass empty AFFECTED_SERVICES.

    # Expected:
    # - Script should pull the release tool image.
    # - Host scripts (refresh secrets, create env, check envs, generate meta) should be called.
    # - Python tool 'generate-units' should be called with empty affected_services.
    # - Quadlet dry run should be called.
    # - Python tool 'pull-images' should be called with empty affected_services.
    # - Python tool 'manage-services restart' should be called with empty affected_services (which then just reloads daemon).
    # - Podman auto-update should be called.
    # - Script should exit 0.

    AFFECTED_SERVICES=""
    VARS_JSON='{"key":"value"}'
    SECRETS_JSON='{"secret_key":"secret_value"}'

    run "$SCRIPT_UNDER_TEST" "$AFFECTED_SERVICES" "$VARS_JSON" "$SECRETS_JSON"

    echo "Status: $status"
    echo "Output: $output"
    [ "$status" -eq 0 ]

    # Verify calls to mocks
    podman_log="$BATS_TMP_DIR/podman_calls.log"
    host_script_log="$BATS_TMP_DIR/host_script_calls.log"
    quadlet_log="$BATS_TMP_DIR/quadlet_calls.log"

    grep -q "MOCK_PODMAN_CALLED: pull ghcr.io/test-owner/continuous_deployment_starter/release-tool:latest" "$podman_log"
    grep -q "MOCK_SCRIPT_CALLED: refresh_podman_secrets.sh {\"secret_key\":\"secret_value\"}" "$host_script_log"
    grep -q "MOCK_SCRIPT_CALLED: create_env_variables.sh" "$host_script_log" # Assuming it doesn't take VARS_JSON as arg yet
    grep -q "MOCK_SCRIPT_CALLED: check-service-envs.sh" "$host_script_log"

    # Check generate-units call (args are long, check key parts)
    grep -q "MOCK_PODMAN_CALLED: run --rm --security-opt label=disable -v $MOCK_SERVICES_DEF_DIR:/app/services:ro,Z -v $MOCK_SYSTEMD_USER_UNITS_DIR:/app/output_units:rw,Z ghcr.io/test-owner/continuous_deployment_starter/release-tool:latest generate-units --affected-services  --services-dir /app/services --output-dir /app/output_units --meta-target all-containers.target --vars-json {\"key\":\"value\"}" "$podman_log"

    grep -q "MOCK_QUADLET_CALLED: --dryrun --user --no-header $MOCK_SYSTEMD_USER_UNITS_DIR" "$quadlet_log"
    grep -q "MOCK_SCRIPT_CALLED: generate_meta_services.sh" "$host_script_log"

    grep -q "MOCK_PODMAN_CALLED: run --rm --security-opt label=disable -v /run/user/.*/podman/podman.sock:/var/run/podman/podman.sock:Z -v $MOCK_SYSTEMD_USER_UNITS_DIR:/app/units:ro,Z ghcr.io/test-owner/continuous_deployment_starter/release-tool:latest pull-images --affected-services  --units-dir /app/units" "$podman_log"
    grep -q "MOCK_PODMAN_CALLED: run --rm --security-opt label=disable -v /run/user/.*/podman/podman.sock:/var/run/podman/podman.sock:Z -v /run/user/.*/bus:/run/systemd/user/bus:Z ghcr.io/test-owner/continuous_deployment_starter/release-tool:latest manage-services restart --affected-services " "$podman_log"

    grep -q "MOCK_PODMAN_CALLED: auto-update" "$podman_log"
}

# TODO: More test cases:
# - Single affected service
# - Multiple affected services
# - podman pull failure for release tool
# - python tool command failure (e.g., generate-units fails)
# - A service fails to restart (python tool manage-services restart exits non-zero)
# - Check if specific files are generated in MOCK_SYSTEMD_USER_UNITS_DIR by generate-units mock call
# - Test different values for VARS_JSON and SECRETS_JSON being passed through
# - Test script exit codes on failure

# Note on path overrides:
# The `deploy_on_host.sh` script hardcodes several paths like PROJECT_DIR_ON_HOST (based on ~USER/runtime/...)
# and SYSTEMD_USER_UNITS_DIR_ON_HOST (based on ~USER/.config/...).
# For robust testing, `deploy_on_host.sh` should be modified to allow these critical paths
# to be overridden by environment variables if those env vars are set.
# Example modification in deploy_on_host.sh:
# SYSTEMD_USER_UNITS_DIR_ON_HOST="${TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR:-$REMOTE_USER_HOME/.config/containers/systemd}"
# SERVICES_DEF_DIR_ON_HOST="${TEST_OVERRIDE_SERVICES_DEF_DIR:-$PROJECT_DIR_ON_HOST/services}"
# This allows tests to set TEST_OVERRIDE_* variables to point to mock directories.
# The setup() function above already exports these TEST_OVERRIDE_* vars.
# This change needs to be made in the actual deploy_on_host.sh script.
```

**Modifications needed in `deploy_on_host.sh` for testability:**

To make the `deploy_on_host.sh` script more testable with the above Bats structure, it should be modified to allow overriding key paths via environment variables. For example:

```bash
# In deploy_on_host.sh
# ...
PROJECT_DIR_ON_HOST="${TEST_OVERRIDE_PROJECT_DIR_ON_HOST:-$REMOTE_USER_HOME/runtime/continuous_deployment_starter}"
SERVICES_DEF_DIR_ON_HOST="${TEST_OVERRIDE_SERVICES_DEF_DIR:-$PROJECT_DIR_ON_HOST/services}"
HOST_SCRIPTS_DIR="${TEST_OVERRIDE_HOST_SCRIPTS_DIR:-$PROJECT_DIR_ON_HOST/.github/workflows/scripts}"
SYSTEMD_USER_UNITS_DIR_ON_HOST="${TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR:-$REMOTE_USER_HOME/.config/containers/systemd}"
QUADLET_PATH="${TEST_OVERRIDE_QUADLET_PATH:-/usr/libexec/podman/quadlet}" # For mocking quadlet executable
# ... then use $QUADLET_PATH instead of hardcoded path later
```
The Bats `setup()` function would then `export TEST_OVERRIDE_...` variables pointing to temporary mock directories.

I will now create the Bats test file. Then, I will modify `deploy_on_host.sh` to include these testability overrides.
