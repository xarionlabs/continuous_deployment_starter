# release_tool/image_manager.py
import subprocess
from pathlib import Path
from typing import List, Optional

def get_image_from_container_file(container_file_path: Path) -> Optional[str]:
    """Parses a .container file and returns the value of the Image= key."""
    if not container_file_path.is_file():
        print(f"Warning: Container file not found: {container_file_path}", flush=True)
        return None

    try:
        with open(container_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith("Image="):
                    return line.split("=", 1)[1]
    except Exception as e:
        print(f"Error reading or parsing container file {container_file_path}: {e}", flush=True)
    return None

def pull_image(image_name: str) -> bool:
    """Pulls a container image using Podman. Returns True on success, False on failure."""
    print(f"Attempting to pull image: {image_name}...", flush=True)
    try:
        # Using shell=False is safer, command and args as a list
        process = subprocess.run(
            ["podman", "pull", image_name],
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit, we'll check manually
        )
        if process.returncode == 0:
            print(f"✅ Successfully pulled image: {image_name}", flush=True)
            # print(process.stdout, flush=True) # Optional: print podman output
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
        return True # No services, so trivially successful

    if not units_dir_path.is_dir():
        print(f"Error: Units directory '{units_dir_path}' does not exist. Cannot find .container files.", flush=True)
        return False

    print(f"Starting image pull process for affected services in units directory: {units_dir_path}", flush=True)
    overall_success = True

    for service_name in affected_services:
        sane_service_name = service_name # Assuming service_name is already sanitized if needed for filenames
        container_file = units_dir_path / f"{sane_service_name}.container"

        image_to_pull = get_image_from_container_file(container_file)

        if image_to_pull:
            if not pull_image(image_to_pull):
                overall_success = False # Continue pulling other images, but mark overall as failed
                print(f"Continuing with other services despite failure to pull {image_to_pull} for {service_name}.", flush=True)
        else:
            print(f"No image found or could not read container file for service '{service_name}'. Skipping image pull for it.", flush=True)
            # Not finding an image for an affected service might be an issue, but script replicates original behavior of just warning.
            # Depending on strictness, this could set overall_success = False

    if overall_success:
        print("Image pulling process completed for all relevant services.", flush=True)
    else:
        print("Image pulling process completed with one or more failures.", flush=True)

    return overall_success
