import subprocess
import time
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple

# --- Systemd Interaction Helpers ---

def _run_systemctl_command(args: List[str], check_return_code: bool = True) -> Tuple[bool, str, str]:
    """Helper to run a systemctl --user command and return success, stdout, stderr."""
    try:
        full_command = ["systemctl", "--user"] + args
        print(f"Executing: {' '.join(full_command)}", flush=True)
        process = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=False
        )
        if check_return_code and process.returncode != 0:
            print(f"Error running {' '.join(full_command)}. RC: {process.returncode}", flush=True)
            if process.stdout: print(f"  Stdout: {process.stdout.strip()}", flush=True)
            if process.stderr: print(f"  Stderr: {process.stderr.strip()}", flush=True)
            return False, process.stdout, process.stderr.strip()
        return True, process.stdout, process.stderr.strip()
    except FileNotFoundError:
        print("Error: 'systemctl' command not found. Is systemd running in user mode?", flush=True)
        return False, "", "systemctl command not found"
    except Exception as e:
        print(f"An unexpected error occurred running systemctl: {e}", flush=True)
        return False, "", str(e)

def service_exists(service_unit_name: str) -> bool:
    """Checks if a systemd user service unit exists (e.g., myapp.service)."""
    # list-unit-files will output the file and its state, or nothing if not found (after filtering)
    if not service_unit_name.endswith(".service"):
        service_unit_name_with_ext = f"{service_unit_name}.service"
    else:
        service_unit_name_with_ext = service_unit_name

    # Using list-units to check if it's loaded/active/failed, list-unit-files for just existence
    success, stdout, _ = _run_systemctl_command(["list-unit-files", "--no-legend", "--quiet", service_unit_name_with_ext], check_return_code=False)
    # list-unit-files has RC 0 even if file not found but pattern is valid.
    # It outputs the filename if it exists.
    return success and service_unit_name_with_ext in stdout

def get_reverse_dependencies(service_unit_name: str) -> Set[str]:
    """
    Gets all reverse dependencies for a service unit (e.g., myapp.service).
    Returns a set of service unit names (e.g., {"dependent1.service", "dependent2.service"}).
    """
    if not service_unit_name.endswith(".service"):
        service_unit_name = f"{service_unit_name}.service"

    rev_deps: Set[str] = set()
    success, stdout, _ = _run_systemctl_command(
        ["list-dependencies", service_unit_name, "--reverse", "--plain"],
        check_return_code=False # Can return non-zero if service has no deps or does not exist
    )
    if success:
        for line in stdout.splitlines():
            dep_unit = line.strip()
            if dep_unit and dep_unit.endswith(".service") and dep_unit != service_unit_name:
                # Further check if this dependency is a real, manageable unit
                # list-units --quiet will have RC 0 if unit is found (any state)
                # check_exists_success, _, _ = _run_systemctl_command(["list-units", "--quiet", "--no-legend", dep_unit], check_return_code=False)
                # if check_exists_success: # This check might be too slow if done for many deps
                rev_deps.add(dep_unit)
    return rev_deps

def reload_systemd_daemon() -> bool:
    """Reloads the systemd --user daemon."""
    print("Reloading systemd --user daemon...", flush=True)
    success, _, _ = _run_systemctl_command(["daemon-reload"])
    if success:
        print("✅ Systemd daemon reloaded successfully.", flush=True)
    else:
        print("❌ Failed to reload systemd daemon.", flush=True)
    return success

def restart_systemd_service(service_unit_name: str) -> bool:
    """Restarts a systemd user service. Returns True on success command issue, False otherwise."""
    if not service_unit_name.endswith(".service"):
        service_unit_name = f"{service_unit_name}.service"
    print(f"Attempting to restart service: {service_unit_name}...", flush=True)
    success, stdout, stderr = _run_systemctl_command(["restart", service_unit_name])
    if success:
        print(f"✅ Restart command issued for {service_unit_name}.", flush=True)
    else:
        print(f"❌ Failed to issue restart for {service_unit_name}.", flush=True)
        # Detailed logs might be printed by _run_systemctl_command already
    return success

def get_service_properties(service_unit_name: str, properties: List[str]) -> Dict[str, str]:
    """Gets specific properties of a systemd user service using 'systemctl show'."""
    if not service_unit_name.endswith(".service"):
        service_unit_name = f"{service_unit_name}.service"

    args = ["show", service_unit_name]
    for prop in properties:
        args.extend(["-p", prop])
    args.append("--value")

    success, stdout, _ = _run_systemctl_command(args, check_return_code=False) # show can fail if service just died

    prop_values: Dict[str, str] = {prop: "unknown" for prop in properties}

    if success:
        lines = stdout.splitlines()
        # systemctl show --value prints one property per line.
        # If a property is empty, it prints an empty line.
        # If a property doesn't exist for the unit, it might omit the line or print specific error marker (less common for --value).
        # We expect as many lines as properties requested if all are valid and found.

        for i, prop_name in enumerate(properties):
            if i < len(lines):
                prop_values[prop_name] = lines[i].strip()
            else:
                # This case means systemctl didn't output enough lines for the requested properties.
                # It might happen if a property is not applicable to a unit type and systemctl omits it.
                print(f"Warning: Property '{prop_name}' may be missing from 'systemctl show' output for {service_unit_name}. Output lines: {len(lines)}, Properties requested: {len(properties)}", flush=True)
    else:
        print(f"Warning: 'systemctl show' command failed for {service_unit_name}. All requested properties marked as 'unknown_command_failed'.", flush=True)
        for prop_name in properties:
            prop_values[prop_name] = "unknown_command_failed"

    return prop_values


def check_one_service_status(service_unit_name: str, max_retries: int = 5, check_interval: int = 5) -> bool:
    """
    Checks the status of a single systemd user service.
    Returns True if active (or successfully completed for oneshot), False otherwise.
    """
    if not service_unit_name.endswith(".service"):
        service_unit_name = f"{service_unit_name}.service"

    print(f"Checking status for {service_unit_name}...", flush=True)

    props_to_get = ["Type", "ActiveState", "SubState", "Result"]

    for attempt in range(max_retries):
        properties = get_service_properties(service_unit_name, props_to_get)
        service_type = properties.get("Type", "unknown")
        active_state = properties.get("ActiveState", "unknown")
        sub_state = properties.get("SubState", "unknown")
        result_state = properties.get("Result", "unknown")

        if service_type == "oneshot":
            if result_state == "success":
                print(f"✅ {service_unit_name} (oneshot) completed successfully.", flush=True)
                return True
            # Oneshot might be 'activating' then 'deactivating' then result is set.
            if result_state not in ["unknown", "unknown_command_failed"] and result_state != "success":
                 print(f"❌ {service_unit_name} (oneshot) is in final state '{result_state}'.", flush=True)
                 return False
        else:
            if active_state == "active":
                print(f"✅ {service_unit_name} is active (SubState: {sub_state}).", flush=True)
                return True
            if active_state == "failed":
                print(f"❌ {service_unit_name} is in a failed state (SubState: {sub_state}).", flush=True)
                return False

        if attempt < max_retries - 1:
            print(f"⏳ {service_unit_name} (Type: {service_type}, ActiveState: {active_state}, SubState: {sub_state}, Result: {result_state}). Retrying in {check_interval}s... ({attempt+1}/{max_retries})", flush=True)
            time.sleep(check_interval)
        else:
            print(f"❌ {service_unit_name} did not reach desired state after {max_retries} retries. Final state: Type: {service_type}, ActiveState: {active_state}, SubState: {sub_state}, Result: {result_state}", flush=True)
            return False
    return False


# --- Main Orchestration Logic for Service Restarts ---

def manage_services_restart(
    affected_services_names: List[str],
    # units_dir_path: Path, # Not directly needed if systemctl knows about the units
    max_status_retries: int = 5,
    status_check_interval: int = 5
) -> bool:
    """
    Manages the restart of affected services and their dependents.
    1. Determines the full set of services to restart (input + reverse dependencies).
    2. Reloads systemd daemon.
    3. Restarts each service in the set.
    4. Checks the status of each restarted service.
    Returns True if all restarted services are healthy, False otherwise.
    """
    if not affected_services_names:
        print("No affected services specified for restart. Reloading daemon just in case.", flush=True)
        reload_systemd_daemon()
        return True

    print(f"Starting service management for restart. Affected base services: {affected_services_names}", flush=True)

    services_to_restart_final: Set[str] = set()
    processed_for_deps: Set[str] = set()

    current_services_to_process: List[str] = [
        f"{name}.service" if not name.endswith(".service") else name for name in affected_services_names
    ]

    # Iteratively find all services that need restart (original + dependents)
    # This loop ensures we find dependents of dependents as well.
    while current_services_to_process:
        service_unit = current_services_to_process.pop(0)
        if service_unit in processed_for_deps:
            continue
        processed_for_deps.add(service_unit)

        if not service_exists(service_unit):
            print(f"Warning: Service '{service_unit}' marked for restart does not exist as a systemd unit. Skipping it.", flush=True)
            continue

        services_to_restart_final.add(service_unit)

        print(f"Finding reverse dependencies for {service_unit}...", flush=True)
        rev_deps = get_reverse_dependencies(service_unit)
        if rev_deps:
            print(f"Found reverse dependencies for {service_unit}: {rev_deps}", flush=True)
            for dep in rev_deps:
                if dep not in processed_for_deps:
                    services_to_restart_final.add(dep)
                    current_services_to_process.append(dep)
        else:
            print(f"No reverse dependencies found for {service_unit}.", flush=True)


    if not services_to_restart_final:
        print("No actual systemd services identified for restart after checking existence and dependencies.", flush=True)
        reload_systemd_daemon() # Still reload, as quadlet files might have changed
        return True

    print(f"Final list of services to restart (including dependents): {sorted(list(services_to_restart_final))}", flush=True)

    if not reload_systemd_daemon():
        print("Critical error: Failed to reload systemd daemon. Aborting service restarts.", flush=True)
        return False

    # Restart services
    # Systemd handles dependency order for restarts if they are properly defined.
    # Restarting one by one.
    all_restarts_issued_successfully = True
    for service_unit in sorted(list(services_to_restart_final)):
        if not restart_systemd_service(service_unit):
            all_restarts_issued_successfully = False
            # Continue trying to restart others, but overall operation will be marked as failed if any issue arises here.

    if not all_restarts_issued_successfully:
         print("One or more services failed to issue the restart command. Check logs above.", flush=True)
         # We might still proceed to status checks for those that were issued.

    print(f"Waiting {status_check_interval} seconds for services to settle after restart commands...", flush=True)
    time.sleep(status_check_interval)

    failed_service_checks: List[str] = []
    print("\n--- Checking Service Statuses ---", flush=True)
    for service_unit in sorted(list(services_to_restart_final)):
        if not check_one_service_status(service_unit, max_retries=max_status_retries, check_interval=status_check_interval):
            failed_service_checks.append(service_unit)
            print(f"🔻 Detailed logs for failed service {service_unit}:", flush=True)
            _run_systemctl_command(["status", "--no-pager", "-n", "50", service_unit], check_return_code=False)
            _run_systemctl_command(["journalctl", "--user", "-u", service_unit, "--no-pager", "--lines=50"], check_return_code=False)

    if failed_service_checks:
        print("\n🔴 Service checks summary: Some services failed to start/complete properly after restart:", flush=True)
        for fs in failed_service_checks:
            print(f"  - {fs}", flush=True)
        return False
    else:
        print(f"\n🎉 All {len(services_to_restart_final)} restarted services are running/completed correctly!", flush=True)
        return True
