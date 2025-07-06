import pytest
import subprocess
import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from unittest import mock

# Path to the script under test, relative from the project root.
SCRIPT_UNDER_TEST = "release-tooling/scripts/deploy_on_host.sh"

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
        "host_scripts": base_dir / "mock_project_on_host" / ".github" / "workflows" / "scripts", # This path is used by TEST_OVERRIDE_HOST_SCRIPTS_DIR
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
    # Ensure the parent of services/version.env exists if services_def is just services/
    (paths["project_on_host"] / "services").mkdir(exist_ok=True)
    (paths["project_on_host"] / "services/version.env").write_text("MOCK_VERSION_VAR=v1.e2e\n")


    return paths

@pytest.fixture
def mock_executables(temp_test_env: Dict[str, Path]):
    """
    Creates mock executables (podman, quadlet, host scripts)
    and prepends their directory to PATH.
    """
    mock_bin_dir = temp_test_env["mock_bin"]
    # Mock host scripts are created in the directory that TEST_OVERRIDE_HOST_SCRIPTS_DIR points to.
    # deploy_on_host.sh, when overridden, will use this path.
    # The actual host scripts for the project are now in release-tooling/scripts/
    # The mock scripts are created under temp_test_env["host_scripts"] which is fine for testing.
    host_scripts_mock_dir = temp_test_env["host_scripts"]
    log_dir = temp_test_env["log_dir"]

    # Mock podman
    podman_mock_path = mock_bin_dir / "podman"
    with open(podman_mock_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"echo \"MOCK_PODMAN_CALLED: $@\" >> \"{log_dir / 'podman_calls.log'}\"\n")
        f.write("if [[ \"$1\" == \"pull\" && \"$2\" == *\"failpull\"* ]]; then exit 1; fi\n")
        f.write("if [[ \"$1\" == \"run\" && \"$*\" == *\"fail-generate\"* ]]; then exit 1; fi\n")
        f.write("exit 0\n")
    os.chmod(podman_mock_path, 0o755)

    # Mock quadlet
    quadlet_mock_path = temp_test_env["mock_quadlet_dir"] / "quadlet" # This creates it in mock_bin/usr/libexec/podman/quadlet
    with open(quadlet_mock_path, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"echo \"MOCK_QUADLET_CALLED: $@\" >> \"{log_dir / 'quadlet_calls.log'}\"\n")
        f.write("exit 0\n")
    os.chmod(quadlet_mock_path, 0o755)

    # Mock host scripts (these are the ones deploy_on_host.sh calls, like refresh_podman_secrets.sh)
    host_script_names = [
        "refresh_podman_secrets.sh", "create_env_variables.sh",
        "check-service-envs.sh", "generate_meta_services.sh",
        "generate-env-from-gh-variables.sh", "check-env.sh" # Add the sub-scripts
    ]
    for script_name in host_script_names:
        script_path = host_scripts_mock_dir / script_name # Create mocks in the dir specified by TEST_OVERRIDE_HOST_SCRIPTS_DIR
        with open(script_path, "w") as f:
            f.write("#!/bin/bash\n")
            f.write(f"echo \"MOCK_SCRIPT_CALLED: {script_name} $@\" >> \"{log_dir / 'host_script_calls.log'}\"\n")
            f.write("exit 0\n")
        os.chmod(script_path, 0o755)

    original_path = os.environ.get("PATH", "")
    # Path for podman mock, and for quadlet mock (its parent dir needs to be in PATH if quadlet is called as /usr/libexec/podman/quadlet)
    # The TEST_OVERRIDE_QUADLET_PATH will directly point to the mock quadlet script.
    # Also add the host_scripts_mock_dir to PATH so that scripts called by other scripts can be found.
    os.environ["PATH"] = f"{mock_bin_dir}:{host_scripts_mock_dir}:{temp_test_env['mock_quadlet_dir'].parent}:{original_path}"
    yield
    os.environ["PATH"] = original_path

def test_deploy_orchestrator_basic_run_no_services(temp_test_env: Dict[str, Path], mock_executables, capsys):
    """
    Test a basic run of deploy_on_host.sh with no affected services.
    """
    env_vars = os.environ.copy()
    env_vars["PYTHON_RELEASE_TOOL_IMAGE"] = "ghcr.io/test-owner/test-release-tool:e2e"
    env_vars["AFFECTED_SERVICES"] = ""
    env_vars["VARS_JSON_STR"] = '{"GLOBAL_VAR":"global_value"}'
    env_vars["SECRETS_JSON_STR"] = '{"SECRET_KEY":"secret_val"}'

    env_vars["TEST_OVERRIDE_PROJECT_DIR_ON_HOST"] = str(temp_test_env["project_on_host"])
    env_vars["TEST_OVERRIDE_SERVICES_DEF_DIR"] = str(temp_test_env["services_def"])
    env_vars["TEST_OVERRIDE_HOST_SCRIPTS_DIR"] = str(temp_test_env["host_scripts"])
    env_vars["TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR"] = str(temp_test_env["systemd_units"])
    env_vars["TEST_OVERRIDE_QUADLET_PATH"] = str(temp_test_env["mock_quadlet_dir"] / "quadlet")

    script_path = Path(SCRIPT_UNDER_TEST)
    absolute_script_path = (Path(os.getcwd()) / script_path).resolve()
    if not absolute_script_path.is_file(): # pragma: no cover
        # Fallback for sandbox where /app is project root
        absolute_script_path_app = Path("/app") / SCRIPT_UNDER_TEST
        if absolute_script_path_app.is_file():
            absolute_script_path = absolute_script_path_app
        else:
            pytest.fail(f"Script under test not found: {SCRIPT_UNDER_TEST} (abs: {absolute_script_path}) or {absolute_script_path_app}")

    os.chmod(absolute_script_path, 0o755)

    result = subprocess.run(
        ["bash", str(absolute_script_path),
         env_vars["AFFECTED_SERVICES"],
         env_vars["VARS_JSON_STR"],
         env_vars["SECRETS_JSON_STR"]],
        env=env_vars, # Still pass env_vars for other settings like TEST_OVERRIDE_* and PATH
        capture_output=True,
        text=True,
        cwd=temp_test_env["project_on_host"] # Run script from within the mock project dir
    )

    print_outputs(result)
    assert result.returncode == 0, "deploy_on_host.sh should exit successfully"

    podman_calls_log = temp_test_env["log_dir"] / "podman_calls.log"
    host_script_calls_log = temp_test_env["log_dir"] / "host_script_calls.log"
    quadlet_calls_log = temp_test_env["log_dir"] / "quadlet_calls.log"

    assert podman_calls_log.exists()
    assert host_script_calls_log.exists()
    assert quadlet_calls_log.exists()

    podman_log_content = podman_calls_log.read_text()
    host_log_content = host_script_calls_log.read_text()
    quadlet_log_content = quadlet_calls_log.read_text()

    assert "MOCK_PODMAN_CALLED: pull ghcr.io/test-owner/test-release-tool:e2e" in podman_log_content
    assert "MOCK_SCRIPT_CALLED: refresh_podman_secrets.sh {\"SECRET_KEY\":\"secret_val\"}" in host_log_content
    assert "MOCK_SCRIPT_CALLED: create_env_variables.sh" in host_log_content
    assert "MOCK_PODMAN_CALLED: run --rm --security-opt label=disable" in podman_log_content
    # For empty affected services, expect '--affected-services' followed by two spaces then the next option, or just the option name if it's the last one.
    # Example log: "... generate-units --affected-services  --services-dir ..."
    assert "generate-units --affected-services  --" in podman_log_content
    assert "vars-json {\"GLOBAL_VAR\":\"global_value\"}" in podman_log_content # This should be fine as JSON string is passed as one arg.
    assert f"MOCK_QUADLET_CALLED: --dryrun --user --no-header {temp_test_env['systemd_units']}" in quadlet_log_content
    assert "MOCK_SCRIPT_CALLED: generate_meta_services.sh" in host_log_content
    assert "pull-images --affected-services  --" in podman_log_content
    assert "manage-services restart --affected-services" in podman_log_content # For restart, it might be the last arg.
    assert "MOCK_PODMAN_CALLED: auto-update" in podman_log_content


def create_dummy_compose_file(services_def_dir: Path, service_name: str):
    """Helper to create a minimal compose file for a service."""
    # Ensure the specific service directory exists under the mocked services_def_dir
    service_path = services_def_dir / service_name
    service_path.mkdir(parents=True, exist_ok=True)

    compose_content = {
        "version": "3.8",
        "services": {
            service_name: {
                "image": f"image_for_{service_name}:latest"
            }
        }
    }
    # The compose file should be in the service's own directory
    with open(service_path / "docker-compose.yml", "w") as f:
        yaml.dump(compose_content, f)

def test_deploy_single_affected_service(temp_test_env: Dict[str, Path], mock_executables, capsys):
    service_name = "service_alpha"
    # Create dummy compose file in the mocked services definition directory
    create_dummy_compose_file(temp_test_env["services_def"], service_name)

    env_vars = os.environ.copy()
    env_vars["PYTHON_RELEASE_TOOL_IMAGE"] = "ghcr.io/test-owner/test-release-tool:e2e"
    env_vars["AFFECTED_SERVICES"] = service_name
    env_vars["VARS_JSON_STR"] = '{}'
    env_vars["SECRETS_JSON_STR"] = '{}'
    env_vars["TEST_OVERRIDE_PROJECT_DIR_ON_HOST"] = str(temp_test_env["project_on_host"])
    env_vars["TEST_OVERRIDE_SERVICES_DEF_DIR"] = str(temp_test_env["services_def"])
    env_vars["TEST_OVERRIDE_HOST_SCRIPTS_DIR"] = str(temp_test_env["host_scripts"])
    env_vars["TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR"] = str(temp_test_env["systemd_units"])
    env_vars["TEST_OVERRIDE_QUADLET_PATH"] = str(temp_test_env["mock_quadlet_dir"] / "quadlet")

    script_path = Path(SCRIPT_UNDER_TEST)
    absolute_script_path = (Path(os.getcwd()) / script_path).resolve()
    if not absolute_script_path.is_file(): # pragma: no cover
        absolute_script_path_app = Path("/app") / SCRIPT_UNDER_TEST
        if absolute_script_path_app.is_file():
            absolute_script_path = absolute_script_path_app
        else:
            pytest.fail(f"Script under test not found: {SCRIPT_UNDER_TEST} or {absolute_script_path_app}")

    result = subprocess.run(
        ["bash", str(absolute_script_path),
         env_vars["AFFECTED_SERVICES"],
         env_vars["VARS_JSON_STR"],
         env_vars["SECRETS_JSON_STR"]],
        env=env_vars, capture_output=True, text=True, cwd=temp_test_env["project_on_host"]
    )
    print_outputs(result)
    assert result.returncode == 0

    podman_log_content = (temp_test_env["log_dir"] / "podman_calls.log").read_text()
    assert f"generate-units --affected-services {service_name}" in podman_log_content
    assert f"pull-images --affected-services {service_name}" in podman_log_content
    assert f"manage-services restart --affected-services {service_name}" in podman_log_content

def print_outputs(result: subprocess.CompletedProcess): # pragma: no cover
    """Helper to print subprocess outputs for debugging."""
    print("--- SCRIPT STDOUT ---")
    print(result.stdout)
    print("--- SCRIPT STDERR ---")
    print(result.stderr)

def test_deploy_multiple_affected_services(temp_test_env: Dict[str, Path], mock_executables, capsys):
    service_alpha = "service_alpha"
    service_beta = "service_beta"
    create_dummy_compose_file(temp_test_env["services_def"], service_alpha)
    create_dummy_compose_file(temp_test_env["services_def"], service_beta)

    affected_services_str = f"{service_alpha} {service_beta}"

    env_vars = os.environ.copy()
    env_vars["PYTHON_RELEASE_TOOL_IMAGE"] = "ghcr.io/test-owner/test-release-tool:e2e"
    env_vars["AFFECTED_SERVICES"] = affected_services_str
    env_vars["VARS_JSON_STR"] = '{"MULTI":"yes"}'
    env_vars["SECRETS_JSON_STR"] = '{}'
    env_vars["TEST_OVERRIDE_PROJECT_DIR_ON_HOST"] = str(temp_test_env["project_on_host"])
    env_vars["TEST_OVERRIDE_SERVICES_DEF_DIR"] = str(temp_test_env["services_def"])
    env_vars["TEST_OVERRIDE_HOST_SCRIPTS_DIR"] = str(temp_test_env["host_scripts"])
    env_vars["TEST_OVERRIDE_SYSTEMD_USER_UNITS_DIR"] = str(temp_test_env["systemd_units"])
    env_vars["TEST_OVERRIDE_QUADLET_PATH"] = str(temp_test_env["mock_quadlet_dir"] / "quadlet")

    script_path = Path(SCRIPT_UNDER_TEST)
    absolute_script_path = (Path(os.getcwd()) / script_path).resolve()
    if not absolute_script_path.is_file(): # pragma: no cover
        absolute_script_path_app = Path("/app") / SCRIPT_UNDER_TEST
        if absolute_script_path_app.is_file():
            absolute_script_path = absolute_script_path_app
        else:
            pytest.fail(f"Script under test not found: {SCRIPT_UNDER_TEST} or {absolute_script_path_app}")

    result = subprocess.run(
        ["bash", str(absolute_script_path),
         env_vars["AFFECTED_SERVICES"],
         env_vars["VARS_JSON_STR"],
         env_vars["SECRETS_JSON_STR"]],
        env=env_vars, capture_output=True, text=True, cwd=temp_test_env["project_on_host"]
    )
    print_outputs(result)
    assert result.returncode == 0

    podman_log_content = (temp_test_env["log_dir"] / "podman_calls.log").read_text()
    assert f"generate-units --affected-services {affected_services_str}" in podman_log_content
    assert f"pull-images --affected-services {affected_services_str}" in podman_log_content
    assert f"manage-services restart --affected-services {affected_services_str}" in podman_log_content


# TODO:
# - Add test for script failure (e.g., podman pull fails)
# - Add test for python tool failure (e.g., generate-units returns non-zero)
# - Verify content of generated unit files in mock_systemd_units for some cases.
# - Test different VARS_JSON and SECRETS_JSON values.
# - Test what happens if a host script is missing.
