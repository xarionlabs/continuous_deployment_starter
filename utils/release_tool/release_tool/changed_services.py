# release_tool/changed_services.py
import os
from pathlib import Path
from typing import List, Set

# These lists define files or path prefixes whose change triggers a full update.
# This replaces the hardcoded list in the bash script.
# We can make this configurable later if needed.
CRITICAL_QUADLET_SCRIPTS_PATTERNS = [
    ".github/workflows/scripts/add_network_names.sh",
    ".github/workflows/scripts/add_volume_names.sh",
    ".github/workflows/scripts/add_partof_services.sh",
    ".github/workflows/scripts/add_oneshot_services.sh",
    ".github/workflows/scripts/add_autoupdate_labels.sh",
    # generate_quadlet_of_service.sh was intentionally removed from forcing all
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
        # typer.echo(f"Warning: Services directory '{services_dir_path}' not found.", err=True) # Use Typer for output in CLI
        print(f"Warning: Services directory '{services_dir_path}' not found.") # Placeholder for now
        return all_services

    for entry in services_dir_path.iterdir():
        if entry.is_dir():
            all_services.add(entry.name)
    return all_services

def determine_affected_services(
    changed_files_str: str,
    assume_value_changes: bool,
    services_dir: str,
    # For testing, allow injecting critical file patterns
    critical_patterns_override: List[str] = None
) -> List[str]:
    """
    Determines the list of affected services based on changed files and flags.
    Returns a list of service names.
    """
    services_dir_path = Path(services_dir)
    all_defined_services = get_all_services(services_dir_path)

    if not all_defined_services:
        # typer.echo("No services found in the services directory.", err=True)
        print("No services found in the services directory.")
        return []

    affected_services_set: Set[str] = set()
    force_update_all = False

    # Use override if provided, else default
    critical_patterns = critical_patterns_override if critical_patterns_override is not None else CRITICAL_GLOBAL_FILES_PATTERNS

    # Convert space-separated string of filenames to a list, handling empty string
    changed_files = [f for f in changed_files_str.split(' ') if f]

    if changed_files:
        for file_path_str in changed_files:
            # Normalize path for consistent matching, e.g., remove leading ./
            normalized_file_path = file_path_str.lstrip('./')

            # Check if the changed file is one of the critical global files
            if any(normalized_file_path == pattern.lstrip('./') for pattern in critical_patterns):
                # typer.echo(f"Critical global file '{file_path_str}' changed. Flagging all services for update.")
                print(f"Critical global file '{file_path_str}' changed. Flagging all services for update.")
                force_update_all = True
                break  # No need to check other files if all are affected

            # Check if the file is within a specific service's directory
            try:
                # Assuming 'services' is the root for service-specific directories
                # e.g., services/my-app/some-file.txt
                path_obj = Path(normalized_file_path)
                if path_obj.parts and path_obj.parts[0] == services_dir_path.name: # e.g. "services"
                    if len(path_obj.parts) > 1:
                        service_name = path_obj.parts[1]
                        if service_name in all_defined_services:
                            affected_services_set.add(service_name)
                            # typer.echo(f"Service '{service_name}' affected by change in '{file_path_str}'.")
                            print(f"Service '{service_name}' affected by change in '{file_path_str}'.")
                        # else: # A directory inside services/ that isn't a known service
                            # typer.echo(f"Change in '{file_path_str}' is under services directory but not a recognized service name.")
            except Exception as e: # pylint: disable=broad-except
                # typer.echo(f"Error processing file path '{file_path_str}': {e}", err=True)
                print(f"Error processing file path '{file_path_str}': {e}")


    if force_update_all:
        # typer.echo("FORCE_UPDATE_ALL is true. All services will be updated.")
        print("FORCE_UPDATE_ALL is true. All services will be updated.")
        return sorted(list(all_defined_services))

    if not changed_files and not affected_services_set and assume_value_changes:
        # typer.echo("No specific code changes detected, but ASSUME_POTENTIAL_VALUE_CHANGES is true. Flagging all services.")
        print("No specific code changes detected, but ASSUME_POTENTIAL_VALUE_CHANGES is true. Flagging all services.")
        return sorted(list(all_defined_services))

    if not affected_services_set:
        # typer.echo("No services determined to be affected.")
        print("No services determined to be affected.")
        return []

    # typer.echo(f"Final list of affected services: {sorted(list(affected_services_set))}")
    print(f"Final list of affected services: {sorted(list(affected_services_set))}")
    return sorted(list(affected_services_set))
