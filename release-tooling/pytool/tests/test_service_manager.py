# tests/test_service_manager.py
import pytest
import subprocess
from unittest import mock
from typing import List, Tuple, Dict

from release_tool import service_manager

# --- Mock subprocess.run consistently ---
class MockSystemctl:
    def __init__(self):
        self.calls = []
        # Expected outputs for specific commands (cmd_tuple -> (rc, stdout, stderr))
        self.mock_outputs: Dict[Tuple[str, ...], Tuple[int, str, str]] = {}
        self.default_rc = 0
        self.default_stdout = ""
        self.default_stderr = ""

    def set_output(self, cmd_args: List[str], returncode: int, stdout: str, stderr: str):
        # Systemctl commands are prefixed with "systemctl --user" by the helper
        key_args = tuple(["systemctl", "--user"] + cmd_args)
        self.mock_outputs[key_args] = (returncode, stdout, stderr)

    def __call__(self, cmd_list: List[str], capture_output: bool, text: bool, check: bool):
        self.calls.append(cmd_list)
        cmd_tuple = tuple(cmd_list)

        rc, stdout, stderr = self.mock_outputs.get(
            cmd_tuple,
            (self.default_rc, self.default_stdout, self.default_stderr)
        )

        if "list-unit-files" in cmd_list and cmd_list[-1] not in stdout and rc==0 : # Simulate file not found for list-unit-files if not in stdout
             # If the specific file isn't in the pre-canned stdout for list-unit-files, simulate it not being found
             # by returning empty stdout, even if default rc is 0.
             # `service_exists` checks if the filename is IN the stdout.
             pass # Let service_exists handle the "in stdout" check

        return subprocess.CompletedProcess(args=cmd_list, returncode=rc, stdout=stdout, stderr=stderr)

@pytest.fixture
def mock_systemctl_runner():
    return MockSystemctl()

@pytest.fixture(autouse=True)
def auto_mock_subprocess_run(monkeypatch, mock_systemctl_runner):
    """Automatically mock subprocess.run for all tests in this file."""
    monkeypatch.setattr(subprocess, "run", mock_systemctl_runner)
    return mock_systemctl_runner


# --- Tests for service_exists ---
def test_service_exists_true(mock_systemctl_runner: MockSystemctl):
    service_name = "testsvc1.service"
    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", service_name], 0, f"{service_name} enabled", "")
    assert service_manager.service_exists("testsvc1") is True
    assert service_manager.service_exists("testsvc1.service") is True

def test_service_exists_false(mock_systemctl_runner: MockSystemctl):
    service_name = "fakesvc.service"
    # list-unit-files rc is 0 even if not found, but stdout is empty or doesn't contain the service
    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", service_name], 0, "", "")
    assert service_manager.service_exists("fakesvc") is False

# --- Tests for get_reverse_dependencies ---
def test_get_reverse_dependencies_found(mock_systemctl_runner: MockSystemctl):
    service = "mainapp.service"
    stdout_deps = "dep1.service\ndep2.service\nmainapp.service\nsome.target"
    mock_systemctl_runner.set_output(["list-dependencies", service, "--reverse", "--plain"], 0, stdout_deps, "")
    # Assume dep1.service and dep2.service "exist" for deeper checks if they were added
    # For this test, the primary check is parsing the output of list-dependencies

    deps = service_manager.get_reverse_dependencies(service)
    assert deps == {"dep1.service", "dep2.service"}

def test_get_reverse_dependencies_none(mock_systemctl_runner: MockSystemctl):
    service = "lonely.service"
    mock_systemctl_runner.set_output(["list-dependencies", service, "--reverse", "--plain"], 0, f"{service}\n", "")
    deps = service_manager.get_reverse_dependencies(service)
    assert deps == set()

# --- Tests for reload_systemd_daemon ---
def test_reload_systemd_daemon_success(mock_systemctl_runner: MockSystemctl):
    mock_systemctl_runner.set_output(["daemon-reload"], 0, "", "")
    assert service_manager.reload_systemd_daemon() is True

def test_reload_systemd_daemon_failure(mock_systemctl_runner: MockSystemctl):
    mock_systemctl_runner.set_output(["daemon-reload"], 1, "", "Failed")
    assert service_manager.reload_systemd_daemon() is False

# --- Tests for restart_systemd_service ---
def test_restart_systemd_service_success(mock_systemctl_runner: MockSystemctl):
    mock_systemctl_runner.set_output(["restart", "app.service"], 0, "", "")
    assert service_manager.restart_systemd_service("app.service") is True

def test_restart_systemd_service_failure(mock_systemctl_runner: MockSystemctl):
    mock_systemctl_runner.set_output(["restart", "app.service"], 1, "", "Error")
    assert service_manager.restart_systemd_service("app.service") is False

# --- Tests for get_service_properties ---
def test_get_service_properties_success(mock_systemctl_runner: MockSystemctl):
    service = "propsvc.service"
    props_to_get = ["Type", "ActiveState"]
    stdout_props = "forking\nactive"
    mock_systemctl_runner.set_output(["show", service, "-p", "Type", "-p", "ActiveState", "--value"], 0, stdout_props, "")

    props = service_manager.get_service_properties(service, props_to_get)
    assert props == {"Type": "forking", "ActiveState": "active"}

def test_get_service_properties_some_missing(mock_systemctl_runner: MockSystemctl):
    service = "propsvc2.service"
    props_to_get = ["Type", "Result"] # Result might be empty if not oneshot or not finished
    # If systemctl show --value for 'Result' is empty, it prints a newline.
    # So, for Type=simple and Result="", the output is "simple\n\n" (or "simple\n \n" if space)
    # Let's assume it's "simple\n\n" which splitlines makes ['simple', '']
    mock_systemctl_runner.set_output(["show", service, "-p", "Type", "-p", "Result", "--value"], 0, "simple\n\n", "") # Corrected mock output

    props = service_manager.get_service_properties(service, props_to_get)
    assert props == {"Type": "simple", "Result": ""}


# --- Tests for check_one_service_status ---
@mock.patch("time.sleep", return_value=None) # Avoid actual sleep
def test_check_one_service_status_active_immediately(mock_sleep, mock_systemctl_runner: MockSystemctl):
    service = "good.service"
    mock_systemctl_runner.set_output(
        ["show", service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "simple\nactive\nrunning\n\n", "" # Added newline for empty Result
    )
    assert service_manager.check_one_service_status(service, max_retries=1, check_interval=1) is True

@mock.patch("time.sleep", return_value=None)
def test_check_one_service_status_becomes_active(mock_sleep, mock_systemctl_runner: MockSystemctl, mocker): # Added mocker
    service = "delayed.service"
    # First call: activating, Second call: active
    show_cmd_args = ["show", service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"]

    call_count = 0

    # Use mocker to specifically patch subprocess.run for this test
    mock_subprocess_run = mocker.patch("subprocess.run")

    def side_effect_for_subprocess_run(cmd_list, capture_output, text, check):
        nonlocal call_count
        # We still want to record calls if other parts of the test infrastructure expect it,
        # but mock_systemctl_runner.calls won't be populated by this specific patch.
        # This test is now self-contained for mocking subprocess.run.
        # However, our _run_systemctl_command calls subprocess.run, so this mock IS subprocess.run
        # We can log calls to the main mock_systemctl_runner.calls if we want, or just check mock_subprocess_run.
        mock_systemctl_runner.calls.append(cmd_list) # Continue to use the main mock for call logging if desired

        expected_cmd_for_show_tuple = tuple(["systemctl", "--user"] + show_cmd_args)
        actual_cmd_tuple = tuple(cmd_list)

        if actual_cmd_tuple == expected_cmd_for_show_tuple:
            call_count += 1
            if call_count == 1:
                return subprocess.CompletedProcess(args=cmd_list, returncode=0, stdout="simple\nactivating\nstarting\n\n", stderr="")
            else:
                return subprocess.CompletedProcess(args=cmd_list, returncode=0, stdout="simple\nactive\nrunning\n\n", stderr="")

        # Fallback for any other unexpected calls if necessary
        return subprocess.CompletedProcess(args=cmd_list, returncode=1, stdout="", stderr="Unexpected call in stateful test")

    mock_subprocess_run.side_effect = side_effect_for_subprocess_run

    assert service_manager.check_one_service_status(service, max_retries=2, check_interval=1) is True
    assert mock_sleep.call_count == 1
    assert mock_subprocess_run.call_count == 2 # Ensure it was called twice for the show command


@mock.patch("time.sleep", return_value=None)
def test_check_one_service_status_oneshot_success(mock_sleep, mock_systemctl_runner: MockSystemctl):
    service = "oneshot_good.service"
    mock_systemctl_runner.set_output(
        ["show", service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "oneshot\ninactive\nexited\nsuccess", ""
    )
    assert service_manager.check_one_service_status(service, max_retries=1, check_interval=1) is True

@mock.patch("time.sleep", return_value=None)
def test_check_one_service_status_fails_max_retries(mock_sleep, mock_systemctl_runner: MockSystemctl):
    service = "bad.service"
    mock_systemctl_runner.set_output(
        ["show", service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "simple\ninactive\ndead\n", "" # Stays inactive
    )
    assert service_manager.check_one_service_status(service, max_retries=2, check_interval=1) is False
    assert mock_sleep.call_count == 1 # Retried once

# --- Tests for manage_services_restart (Orchestration) ---
# These are more integration-like for the module

def test_manage_services_restart_simple_success(mock_systemctl_runner: MockSystemctl):
    services_to_restart = ["app1"]
    app1_service = "app1.service"

    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", app1_service], 0, app1_service, "") # Exists
    mock_systemctl_runner.set_output(["list-dependencies", app1_service, "--reverse", "--plain"], 0, app1_service, "") # No rev deps
    mock_systemctl_runner.set_output(["daemon-reload"], 0, "", "")
    mock_systemctl_runner.set_output(["restart", app1_service], 0, "", "")
    mock_systemctl_runner.set_output(
        ["show", app1_service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "simple\nactive\nrunning\n\n", "" # Added newline
    )

    with mock.patch("time.sleep", return_value=None): # Mock sleep during status checks
        assert service_manager.manage_services_restart(services_to_restart) is True

def test_manage_services_restart_with_dependents(mock_systemctl_runner: MockSystemctl):
    # app1 is affected, dep_on_app1 depends on app1
    app1_service = "app1.service"
    dep_service = "dep_on_app1.service"

    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", app1_service], 0, app1_service, "")
    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", dep_service], 0, dep_service, "")

    # app1 has dep_on_app1 as a reverse dependency
    mock_systemctl_runner.set_output(["list-dependencies", app1_service, "--reverse", "--plain"], 0, f"{dep_service}\n{app1_service}", "")
    # dep_on_app1 has no further reverse dependencies relevant here
    mock_systemctl_runner.set_output(["list-dependencies", dep_service, "--reverse", "--plain"], 0, dep_service, "")

    mock_systemctl_runner.set_output(["daemon-reload"], 0, "", "")
    mock_systemctl_runner.set_output(["restart", app1_service], 0, "", "")
    mock_systemctl_runner.set_output(["restart", dep_service], 0, "", "")

    mock_systemctl_runner.set_output(
        ["show", app1_service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "simple\nactive\nrunning\n\n", "" # Added newline
    )
    mock_systemctl_runner.set_output(
        ["show", dep_service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "simple\nactive\nrunning\n\n", "" # Added newline
    )

    with mock.patch("time.sleep", return_value=None):
        assert service_manager.manage_services_restart(["app1"]) is True

    # Check that restart was called for both
    # mock_systemctl_runner.calls contains list of lists, e.g., [['systemctl', '--user', 'restart', 'app1.service'], ...]
    actual_restart_commands = [cmd_list for cmd_list in mock_systemctl_runner.calls if len(cmd_list) >= 4 and cmd_list[2] == "restart"]

    restarted_services_found = {cmd_list[3] for cmd_list in actual_restart_commands} # Get the service name from the command
    assert app1_service in restarted_services_found
    assert dep_service in restarted_services_found


def test_manage_services_restart_one_fails_status_check(mock_systemctl_runner: MockSystemctl):
    services_to_restart = ["badapp"]
    badapp_service = "badapp.service"

    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", badapp_service], 0, badapp_service, "")
    mock_systemctl_runner.set_output(["list-dependencies", badapp_service, "--reverse", "--plain"], 0, badapp_service, "")
    mock_systemctl_runner.set_output(["daemon-reload"], 0, "", "")
    mock_systemctl_runner.set_output(["restart", badapp_service], 0, "", "") # Restart command succeeds
    mock_systemctl_runner.set_output( # But status check shows failed
        ["show", badapp_service, "-p", "Type", "-p", "ActiveState", "-p", "SubState", "-p", "Result", "--value"],
        0, "simple\nfailed\nfailed\n", ""
    )

    with mock.patch("time.sleep", return_value=None):
        assert service_manager.manage_services_restart(services_to_restart) is False

def test_manage_services_restart_non_existent_service(mock_systemctl_runner: MockSystemctl):
    # nonexist.service does not exist
    mock_systemctl_runner.set_output(["list-unit-files", "--no-legend", "--quiet", "nonexist.service"], 0, "", "")
    mock_systemctl_runner.set_output(["daemon-reload"], 0, "", "") # Daemon reload will still be called

    with mock.patch("time.sleep", return_value=None):
        assert service_manager.manage_services_restart(["nonexist"]) is True # True because no actual services were found to fail

    # Check that restart was not called for nonexist.service
    assert not any("restart" in call[2] and "nonexist.service" in call[3] for call in mock_systemctl_runner.calls)


def test_manage_services_restart_empty_list(mock_systemctl_runner: MockSystemctl):
    mock_systemctl_runner.set_output(["daemon-reload"], 0, "", "")
    assert service_manager.manage_services_restart([]) is True
    # Ensure daemon-reload was called
    assert any(call == ["systemctl", "--user", "daemon-reload"] for call in mock_systemctl_runner.calls)

# TODO: Add tests for:
# - Complex dependency chains for get_reverse_dependencies (dependents of dependents)
# - Restart command itself failing for a service
# - Different oneshot results during status check
# - Error handling when systemctl command itself is not found (FileNotFoundError in _run_systemctl_command)
# - Behavior when units_dir_path is actually used (if it ever is by this module)
# - Iterative discovery of reverse dependencies in manage_services_restart more thoroughly.Tool output for `create_file_with_block`:
