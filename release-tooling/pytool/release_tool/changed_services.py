import os
from pathlib import Path
from typing import List, Set

CRITICAL_QUADLET_SCRIPTS_PATTERNS = [
    ".github/workflows/scripts/add_network_names.sh",
    ".github/workflows/scripts/add_volume_names.sh",
    ".github/workflows/scripts/add_partof_services.sh",
    ".github/workflows/scripts/add_oneshot_services.sh",
    ".github/workflows/scripts/add_autoupdate_labels.sh",
    ".github/workflows/scripts/generate_meta_services.sh",
    ".github/workflows/scripts/generate_quadlets.sh",
]

CRITICAL_ENV_SECRET_SCRIPTS_PATTERNS = [
    ".github/workflows/scripts/create_env_variables.sh",
    ".github/workflows/scripts/check-env.sh",
    ".github/workflows/scripts/check-service-envs.sh",
    ".github/workflows/scripts/generate-env-from-gh-variables.sh",
    ".github/workflows/scripts/add_secrets_to_env.sh",
    ".github/workflows/scripts/refresh_podman_secrets.sh",
]

CRITICAL_WORKFLOW_FILES = [
    ".github/workflows/release.yml",
]

CRITICAL_GLOBAL_FILES_PATTERNS = (
    CRITICAL_QUADLET_SCRIPTS_PATTERNS +
    CRITICAL_ENV_SECRET_SCRIPTS_PATTERNS +
    CRITICAL_WORKFLOW_FILES
)

def get_all_services(services_dir_path: Path) -> Set[str]:
    """Scans the services directory and returns a set of all service names."""
    all_services: Set[str] = set()
    if not services_dir_path.is_dir():
        print(f"Warning: Services directory '{services_dir_path}' not found.")
        return all_services

    for entry in services_dir_path.iterdir():
        if entry.is_dir():
            all_services.add(entry.name)
    return all_services

def determine_affected_services(
    changed_files_str: str,
    assume_value_changes: bool,
    services_dir: str,
    critical_patterns_override: List[str] = None
) -> List[str]:
    """
    Determines the list of affected services based on changed files and flags.
    Returns a list of service names.
    """
    services_dir_path = Path(services_dir)
    all_defined_services = get_all_services(services_dir_path)

    if not all_defined_services:
        print("No services found in the services directory.")
        return []

    affected_services_set: Set[str] = set()
    force_update_all = False

    critical_patterns = critical_patterns_override if critical_patterns_override is not None else CRITICAL_GLOBAL_FILES_PATTERNS
    changed_files = [f for f in changed_files_str.split(' ') if f]

    if changed_files:
        for file_path_str in changed_files:
            normalized_file_path = file_path_str.lstrip('./')

            if any(normalized_file_path == pattern.lstrip('./') for pattern in critical_patterns):
                print(f"Critical global file '{file_path_str}' changed. Flagging all services for update.")
                force_update_all = True
                break

            try:
                path_obj = Path(normalized_file_path)
                if path_obj.parts and path_obj.parts[0] == services_dir_path.name:
                    if len(path_obj.parts) > 1:
                        service_name = path_obj.parts[1]
                        if service_name in all_defined_services:
                            affected_services_set.add(service_name)
                            print(f"Service '{service_name}' affected by change in '{file_path_str}'.")
            except Exception as e: # pylint: disable=broad-except
                print(f"Error processing file path '{file_path_str}': {e}")


    if force_update_all:
        print("FORCE_UPDATE_ALL is true. All services will be updated.")
        return sorted(list(all_defined_services))

    if not changed_files and not affected_services_set and assume_value_changes:
        print("No specific code changes detected, but ASSUME_POTENTIAL_VALUE_CHANGES is true. Flagging all services.")
        return sorted(list(all_defined_services))

    if not affected_services_set:
        print("No services determined to be affected.")
        return []

    print(f"Final list of affected services: {sorted(list(affected_services_set))}")
    return sorted(list(affected_services_set))
