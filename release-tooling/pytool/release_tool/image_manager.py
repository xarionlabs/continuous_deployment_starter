import subprocess
from pathlib import Path
from typing import List, Optional

def get_image_from_container_file(container_file_path: Path) -> Optional[str]:
    """Parses a .container file and returns the value of the Image= key."""
    if not container_file_path.is_file():
        print(f"Warning: Container file not found: {container_file_path}", flush=True)
        return None

    try:
        in_container_section = False
        with open(container_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    in_container_section = (line == "[Container]")

                if in_container_section and line.startswith("Image="):
                    parts = line.split("=", 1)
                    if len(parts) == 2 and parts[1].strip():
                        return parts[1].strip()
                    else:
                        print(f"Warning: Malformed Image= line in {container_file_path}: '{line}'", flush=True)
                        return None
        return None
    except Exception as e:
        print(f"Error reading or parsing container file {container_file_path}: {e}", flush=True)
    return None

def pull_image(image_name: str) -> bool:
    """Pulls a container image using Podman. Returns True on success, False on failure."""
    print(f"Attempting to pull image: {image_name}...", flush=True)
    try:
        process = subprocess.run(
            ["podman", "pull", image_name],
            capture_output=True,
            text=True,
            check=False
        )
        if process.returncode == 0:
            print(f"✅ Successfully pulled image: {image_name}", flush=True)
            return True
        else:
            print(f"⚠️ Failed to pull image: {image_name}. Return code: {process.returncode}", flush=True)
            if process.stdout:
                print(f"   Stdout:\n{process.stdout}", flush=True)
            if process.stderr:
                print(f"   Stderr:\n{process.stderr}", flush=True)
            return False
    except FileNotFoundError:
        print("Error: 'podman' command not found. Is Podman installed and in PATH?", flush=True)
        return False
    except Exception as e:
        print(f"An unexpected error occurred while trying to pull {image_name}: {e}", flush=True)
        return False

def pull_images_for_services(
    affected_services: List[str],
    units_dir_path: Path
) -> bool:
    """
    Pulls container images for the specified list of affected services.
    It looks for <service_name>.container files in the units_dir_path.
    Returns True if all attempted pulls were successful or no pulls were needed,
    False if any pull explicitly failed.
    """
    if not affected_services:
        print("No affected services provided for image pulling. Nothing to do.", flush=True)
        return True

    if not units_dir_path.is_dir():
        print(f"Error: Units directory '{units_dir_path}' does not exist. Cannot find .container files.", flush=True)
        return False

    print(f"Starting image pull process for affected services in units directory: {units_dir_path}", flush=True)
    overall_success = True

    for service_name in affected_services:
        container_file = units_dir_path / f"{service_name}.container"

        image_to_pull = get_image_from_container_file(container_file)

        if image_to_pull:
            if not pull_image(image_to_pull):
                overall_success = False
                print(f"Continuing with other services despite failure to pull {image_to_pull} for {service_name}.", flush=True)
        else:
            print(f"No image found or could not read container file for service '{service_name}'. Skipping image pull for it.", flush=True)
            # Failure to find an image for an *affected* service might be an issue.
            # Current behavior is to warn and continue; overall_success is not impacted by this specific case.

    if overall_success:
        print("Image pulling process completed for all relevant services.", flush=True)
    else:
        print("Image pulling process completed with one or more failures.", flush=True)

    return overall_success
