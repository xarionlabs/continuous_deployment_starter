# tests/e2e_orchestrator/test_deploy_orchestrator.py
import pytest
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, List
from unittest import mock

# Path to the script under test. Assumes pytest is run from `utils/release_tool/` directory.
SCRIPT_UNDER_TEST = "../../.github/workflows/scripts/deploy_on_host.sh"

@pytest.fixture
def temp_test_env(tmp_path: Path) -> Dict[str, Path]:
    """
    Sets up a temporary, isolated environment for testing deploy_on_host.sh.
    Returns a dictionary of key paths.
    """
    base_dir = tmp_path / "e2e_test_run"
    base_dir.mkdir()

    paths = {
        "base": base_dir,
        "project_on_host": base_dir / "mock_project_on_host",
        "services_def": base_dir / "mock_project_on_host" / "services",
        "host_scripts": base_dir / "mock_project_on_host" / ".github" / "workflows" / "scripts",
        "systemd_units": base_dir / "mock_systemd_units",
        "mock_bin": base_dir / "mock_bin", # For mock executables like podman, quadlet
        "mock_quadlet_dir": base_dir / "mock_bin" / "usr" / "libexec" / "podman", # for quadlet mock
        "log_dir": base_dir / "logs" # To store logs from mocks
    }

    paths["services_def"].mkdir(parents=True, exist_ok=True)
    paths["host_scripts"].mkdir(parents=True, exist_ok=True)
    paths["systemd_units"].mkdir(parents=True, exist_ok=True)
    paths["mock_bin"].mkdir(parents=True, exist_ok=True)
    paths["mock_quadlet_dir"].mkdir(parents=True, exist_ok=True)
    paths["log_dir"].mkdir(parents=True, exist_ok=True)

    # Create a dummy .env and version.env in the mock project dir
    (paths["project_on_host"] / ".env").write_text("MOCK_PROJECT_ENV_VAR=from_project_dotenv\n")
    (paths["services_def"].parent / "services/version.env").write_text("MOCK_VERSION_VAR=v1.e2e\n")


    return paths

@pytest.fixture
def mock_executables(temp_test_env: Dict[str, Path]):
    """
    Creates mock executables (podman, quadlet, host scripts)
    and prepends their directory to PATH.
    """
    mock_bin_dir = temp_test_env["mock_bin"]
    host_scripts_dir = temp_test_env["host_scripts"] # These are where deploy_on_host expects to find them
    log_dir = temp_test_env["log_dir"]

    # Mock podman
    podman_mock_path = mock_bin_dir / "podman"
    with open(podman_mock_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"echo \"MOCK_PODMAN_CALLED: $@\" >> \"{log_dir / 'podman_calls.log'}\"\n")
        f.write("if [[ \"$1\" == \"pull\" && \"$2\" == *\"failpull\"* ]]; then exit 1; fi\n") # Simulate pull failure
        f.write("if [[ \"$1\" == \"run\" && \"$*\" == *\"fail-generate\"* ]]; then exit 1; fi\n") # Simulate tool failure
        f.write("exit 0\n")
    os.chmod(podman_mock_path, 0o755)

    # Mock quadlet
    quadlet_mock_path = temp_test_env["mock_quadlet_dir"] / "quadlet"
    with open(quadlet_mock_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"echo \"MOCK_QUADLET_CALLED: $@\" >> \"{log_dir / 'quadlet_calls.log'}\"\n")
        f.write("exit 0\n")
    os.chmod(quadlet_mock_path, 0o755)

    # Mock host scripts
    host_script_names = [
        "refresh_podman_secrets.sh", "create_env_variables.sh",
        "check-service-envs.sh", "generate_meta_services.sh"
    ]
    for script_name in host_script_names:
        script_path = host_scripts_dir / script_name
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"echo \"MOCK_SCRIPT_CALLED: {script_name} $@\" >> \"{log_dir / 'host_script_calls.log'}\"\n")
            f.write("exit 0\n")
        os.chmod(script_path, 0o755)

    # Prepend mock_bin to PATH for the subprocess call
    original_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{mock_bin_dir}:{original_path}"
    yield # Test runs here
    os.environ["PATH"] = original_path # Restore original PATH

def test_deploy_orchestrator_basic_run_no_services(temp_test_env: Dict[str, Path], mock_executables, capsys):
    """
    Test a basic run of deploy_on_host.sh with no affected services.
    """
    env_vars = os.environ.copy()
    env_vars["AFFECTED_SERVICES"] = ""
    env_vars["VARS_JSON_STR"] = '{"GLOBAL_VAR":"global_value"}'
    env_vars["SECRETS_JSON_STR"] = '{"SECRET_KEY":"secret_val"}'

    # Set override paths for deploy_on_host.sh
    env_vars["TEST_OVERRIDE_PROJECT_DIR_ON_HOST"] = str(temp_test_env["project_on_host"])
    env_vars["TEST_OVERRIDE_SERVICES_DEF_DIR"] = str(temp_test_env["services_def"])
    env_vars["TEST_OVERRIDE_HOST_SCRIPTS_DIR"] = str(temp_test_env["host_scripts"])
    env_vars["TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR"] = str(temp_test_env["systemd_units"])
    env_vars["TEST_OVERRIDE_QUADLET_PATH"] = str(temp_test_env["mock_quadlet_dir"] / "quadlet")
    # TEST_OVERRIDE_PODMAN_SOCKET could be set if needed, but mock podman doesn't use it.

    # Ensure the script under test is found and executable
    script_path = Path(SCRIPT_UNDER_TEST)
    if not script_path.is_file():
        # Try absolute path for sandbox
        script_path_abs = Path("/app") / SCRIPT_UNDER_TEST
        if script_path_abs.is_file():
            script_path = script_path_abs
        else:
            pytest.fail(f"Script under test not found: {SCRIPT_UNDER_TEST} or {script_path_abs}")

    os.chmod(script_path, 0o755)


    result = subprocess.run(
        ["bash", str(script_path)],
        env=env_vars,
        capture_output=True,
        text=True,
        cwd=temp_test_env["base"] # Run from a neutral base directory
    )

    # Print script output for debugging if test fails
    print("--- deploy_on_host.sh STDOUT ---")
    print(result.stdout)
    print("--- deploy_on_host.sh STDERR ---")
    print(result.stderr)

    assert result.returncode == 0, "deploy_on_host.sh should exit successfully"

    # Verify mock calls (example assertions)
    podman_calls_log = temp_test_env["log_dir"] / "podman_calls.log"
    host_script_calls_log = temp_test_env["log_dir"] / "host_script_calls.log"
    quadlet_calls_log = temp_test_env["log_dir"] / "quadlet_calls.log"

    assert podman_calls_log.exists()
    assert host_script_calls_log.exists()
    assert quadlet_calls_log.exists()

    podman_log_content = podman_calls_log.read_text()
    host_log_content = host_script_calls_log.read_text()
    quadlet_log_content = quadlet_calls_log.read_text()

    assert "MOCK_PODMAN_CALLED: pull ghcr.io/test-owner/" in podman_log_content
    assert "MOCK_SCRIPT_CALLED: refresh_podman_secrets.sh {\"SECRET_KEY\":\"secret_val\"}" in host_log_content
    assert "MOCK_SCRIPT_CALLED: create_env_variables.sh" in host_log_content # Assuming no args for now
    assert "MOCK_PODMAN_CALLED: run --rm --security-opt label=disable" in podman_log_content
    assert "generate-units --affected-services \"\"" in podman_log_content
    assert "vars-json {\"GLOBAL_VAR\":\"global_value\"}" in podman_log_content
    assert f"MOCK_QUADLET_CALLED: --dryrun --user --no-header {temp_test_env['systemd_units']}" in quadlet_log_content
    assert "MOCK_SCRIPT_CALLED: generate_meta_services.sh" in host_log_content
    assert "pull-images --affected-services \"\"" in podman_log_content
    assert "manage-services restart --affected-services \"\"" in podman_log_content
    assert "MOCK_PODMAN_CALLED: auto-update" in podman_log_content


def create_dummy_compose_file(service_dir: Path, service_name: str):
    """Helper to create a minimal compose file for a service."""
    compose_content = {
        "version": "3.8",
        "services": {
            service_name: {
                "image": f"image_for_{service_name}:latest"
            }
        }
    }
    with open(service_dir / f"{service_name}.compose.yml", "w") as f:
        yaml.dump(compose_content, f) # Requires PyYAML to be available in test env if not already

def test_deploy_single_affected_service(temp_test_env: Dict[str, Path], mock_executables, capsys):
    service_name = "service_alpha"
    create_dummy_compose_file(temp_test_env["services_def"] / service_name, service_name)

    env_vars = os.environ.copy()
    env_vars["AFFECTED_SERVICES"] = service_name
    env_vars["VARS_JSON_STR"] = '{}'
    env_vars["SECRETS_JSON_STR"] = '{}'
    env_vars["TEST_OVERRIDE_PROJECT_DIR_ON_HOST"] = str(temp_test_env["project_on_host"])
    env_vars["TEST_OVERRIDE_SERVICES_DEF_DIR"] = str(temp_test_env["services_def"])
    env_vars["TEST_OVERRIDE_HOST_SCRIPTS_DIR"] = str(temp_test_env["host_scripts"])
    env_vars["TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR"] = str(temp_test_env["systemd_units"])
    env_vars["TEST_OVERRIDE_QUADLET_PATH"] = str(temp_test_env["mock_quadlet_dir"] / "quadlet")

    script_path = Path(SCRIPT_UNDER_TEST)
    if not script_path.is_file():
        script_path_abs = Path("/app") / SCRIPT_UNDER_TEST
        script_path = script_path_abs if script_path_abs.is_file() else script_path

    result = subprocess.run(
        ["bash", str(script_path)], env=env_vars, capture_output=True, text=True, cwd=temp_test_env["base"]
    )
    print_outputs(result)
    assert result.returncode == 0

    podman_log_content = (temp_test_env["log_dir"] / "podman_calls.log").read_text()
    assert f"generate-units --affected-services \"{service_name}\"" in podman_log_content
    assert f"pull-images --affected-services \"{service_name}\"" in podman_log_content
    assert f"manage-services restart --affected-services \"{service_name}\"" in podman_log_content

    # Verify that the mock podman run for generate-units would have created a dummy file
    # This means enhancing the podman mock to simulate file creation if a certain command is seen.
    # For now, we just check the call.
    # A more advanced check would be:
    # assert (temp_test_env["systemd_units"] / f"{service_name}.container").exists()
    # This requires the mock 'podman run ... generate-units' to actually touch that file.
    # The current mock 'podman' doesn't do that.

def print_outputs(result: subprocess.CompletedProcess): # pragma: no cover
    """Helper to print subprocess outputs for debugging."""
    print("--- SCRIPT STDOUT ---")
    print(result.stdout)
    print("--- SCRIPT STDERR ---")
    print(result.stderr)


# TODO:
# - Add test for multiple affected services
# - Add test for script failure (e.g., podman pull fails)
# - Add test for python tool failure (e.g., generate-units returns non-zero)
# - Verify content of generated unit files in mock_systemd_units for some cases.
# - Test different VARS_JSON and SECRETS_JSON values.
# - Test what happens if a host script is missing.
```
