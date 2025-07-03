# release_tool/unit_generator.py
import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# --- Constants for Quadlet Generation ---
# These would be equivalent to settings or conventions used by the add_*.sh scripts

# Example: Default network if not specified, or how to handle host networking
DEFAULT_NETWORK_SETTINGS = {"driver": "bridge"}

# Example: Prefix or convention for volume names
VOLUME_NAME_PREFIX = "podman_vol_"

# --- Data Structures for Quadlet Units (Simple representations) ---

class QuadletUnit:
    """Base class for a Quadlet unit file representation."""
    def __init__(self, unit_type: str, service_name: str):
        self.unit_type = unit_type # e.g., "container", "network", "volume"
        self.service_name = service_name
        self.sections: Dict[str, Dict[str, Any]] = {} # E.g. {"Unit": {"Description": ...}, "Service": {}, "X-Container": {}}

    def add_entry(self, section: str, key: str, value: Any):
        if section not in self.sections:
            self.sections[section] = {}

        # Handle multi-value keys by converting to list if needed
        if key in self.sections[section]:
            current_value = self.sections[section][key]
            if isinstance(current_value, list):
                if isinstance(value, list):
                    self.sections[section][key].extend(value)
                else:
                    self.sections[section][key].append(value)
            else:
                # Convert existing single value to list and add new value(s)
                new_list = [current_value]
                if isinstance(value, list):
                    new_list.extend(value)
                else:
                    new_list.append(value)
                self.sections[section][key] = new_list
        else: # New key
            self.sections[section][key] = value

    def generate_file_content(self) -> str:
        content = []
        for section_name, entries in self.sections.items():
            content.append(f"[{section_name}]")
            for key, value in entries.items():
                if isinstance(value, list):
                    for item in value:
                        content.append(f"{key}={item}")
                elif isinstance(value, bool):
                    content.append(f"{key}={'true' if value else 'false'}")
                else:
                    content.append(f"{key}={value}")
            content.append("") # Blank line after section
        return "\n".join(content)

    def get_filename(self) -> str:
        return f"{self.service_name}.{self.unit_type}"

class ContainerUnit(QuadletUnit):
    def __init__(self, service_name: str):
        super().__init__("container", service_name)
        self.add_entry("Unit", "Description", f"Podman container for {service_name}")
        self.add_entry("Unit", "DefaultDependencies", "false") # Common default
        self.add_entry("Install", "WantedBy", "default.target") # Common default

class VolumeUnit(QuadletUnit):
    def __init__(self, volume_name: str, service_name: Optional[str] = None):
        # service_name is optional here, if the volume is globally defined vs service-specific
        actual_name = service_name if service_name else volume_name
        super().__init__("volume", actual_name) # Use service_name for filename if part of a service bundle
        self.volume_name_on_host = volume_name # The actual name Podman will use
        self.add_entry("Unit", "Description", f"Podman volume {volume_name}")
        self.add_entry("Volume", "Name", self.volume_name_on_host)
        # self.add_entry("Install", "WantedBy", "default.target") # Volumes usually don't need this

class NetworkUnit(QuadletUnit):
    def __init__(self, network_name: str, service_name: Optional[str] = None):
        actual_name = service_name if service_name else network_name
        super().__init__("network", actual_name)
        self.network_name_on_host = network_name
        self.add_entry("Unit", "Description", f"Podman network {network_name}")
        self.add_entry("Network", "Name", self.network_name_on_host)
        # self.add_entry("Install", "WantedBy", "default.target") # Networks usually don't need this

# --- Helper Functions ---

def parse_compose_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Parses a Docker Compose YAML file."""
    if not file_path.is_file():
        print(f"Error: Compose file not found at {file_path}", flush=True)
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file {file_path}: {e}", flush=True)
        return None
    except Exception as e:
        print(f"An unexpected error occurred reading {file_path}: {e}", flush=True)
        return None

def sanitize_service_name_for_filename(service_name: str) -> str:
    """Sanitizes a service name to be used in a filename (e.g. for systemd)."""
    # Replace problematic characters with underscores or remove them
    # This is a basic example; more robust sanitization might be needed.
    name = re.sub(r'[^a-zA-Z0-9_.-]+', '_', service_name)
    return name

# --- Core Conversion Logic (to be expanded) ---

def convert_compose_service_to_container_unit(
    service_name: str,
    compose_service_config: Dict[str, Any],
    all_compose_config: Dict[str, Any], # Full compose file for context (networks, volumes)
    global_env_vars: Optional[Dict[str, str]] = None
) -> Tuple[Optional[ContainerUnit], List[QuadletUnit]]:
    """
    Converts a single service definition from Docker Compose to a ContainerUnit
    and any associated NetworkUnits or VolumeUnits if defined implicitly.
    """
    sane_service_name = sanitize_service_name_for_filename(service_name)
    container_unit = ContainerUnit(sane_service_name)
    auxiliary_units: List[QuadletUnit] = [] # For networks/volumes created on-the-fly

    # Image
    if 'image' in compose_service_config:
        container_unit.add_entry("Container", "Image", compose_service_config['image'])
    else:
        # build context might imply an image name or need one to be generated/tagged
        # Quadlet typically expects an image name.
        print(f"Warning: Service '{service_name}' has no 'image' defined. Build contexts are not directly translated by this basic converter.", flush=True)
        # For now, we'll skip services without a direct image. A real tool might try to infer or require it.
        return None, []


    # --- Basic Mappings (Examples) ---
    if 'container_name' in compose_service_config: # Podman equivalent is Name
        container_unit.add_entry("Container", "PodmanArgs", f"--name={compose_service_config['container_name']}")
    else: # Default name for podman if not specified by compose
        container_unit.add_entry("Container", "PodmanArgs", f"--name={sane_service_name}")


    # Ports (simplified: only maps to PodmanArgs --publish)
    # Quadlet also has Port= key which is often preferred
    if 'ports' in compose_service_config:
        for port_mapping in compose_service_config['ports']:
            # Format: "HOST:CONTAINER" or "CONTAINER" (implies random host port)
            # More complex: "IP:HOST:CONTAINER"
            # Quadlet prefers: Port=hostport:containerport
            if isinstance(port_mapping, (str, int)):
                parts = str(port_mapping).split(':')
                if len(parts) == 1: # "CONTAINER"
                    container_unit.add_entry("Container", "Port", parts[0])
                elif len(parts) == 2: # "HOST:CONTAINER"
                     container_unit.add_entry("Container", "Port", f"{parts[0]}:{parts[1]}")
                else: # More complex, add as raw Podman arg for now
                    container_unit.add_entry("Container", "PodmanArgs", f"--publish={port_mapping}")
            else: # E.g. dictionary format for ports (long syntax)
                 print(f"Warning: Complex port definition for service '{service_name}' not fully translated: {port_mapping}", flush=True)


    # Environment variables
    # Priority:
    # 1. Service-specific environment variables from compose
    # 2. Global environment variables from VARS_JSON
    # Service-specific will override global if keys conflict.

    # Start with a copy of global env vars if provided
    final_env: Dict[str, Optional[str]] = {}
    if global_env_vars:
        final_env.update(global_env_vars)

    # Then apply/override with service-specific env vars from compose
    if 'environment' in compose_service_config:
        compose_env_vars = compose_service_config['environment']
        if isinstance(compose_env_vars, dict):
            final_env.update(compose_env_vars) # Dict update handles overrides
        elif isinstance(compose_env_vars, list): # List of "KEY=VALUE" or "KEY"
            for item in compose_env_vars:
                if '=' in item:
                    key, value = item.split('=', 1)
                    final_env[key] = value
                else:
                    # Per user feedback, key-only variables are not supported. Log a warning.
                    print(f"Warning: Service '{service_name}' environment list contains key-only entry '{item}'. This is not supported and will be ignored.", flush=True)

    # Add the combined environment variables to the container unit
    for key, value in final_env.items():
         container_unit.add_entry("Container", "Environment", f"{key}={value if value is not None else ''}")

    # TODO: Volumes (complex: named volumes, host binds, tmpfs)
    # This needs to handle creating VolumeUnit if a named volume is used and not globally defined.
    # And map host binds to Volume=host:container:options

    # TODO: Networks (complex: connecting to existing, creating, aliases)
    # This needs to handle creating NetworkUnit if a network is used and not globally defined.

    # TODO: depends_on -> translate to systemd Requires= and After= for .service files
    # This is handled by adding to the .service file later.
    # The ContainerUnit itself doesn't usually get these.

    # Restart policy
    if 'restart' in compose_service_config:
        policy = compose_service_config['restart']
        # Basic mapping, Quadlet/systemd has more nuanced options
        if policy == "always":
            container_unit.add_entry("Container", "Restart", "always")
        elif policy == "on-failure":
            container_unit.add_entry("Container", "Restart", "on-failure")
        elif policy == "unless-stopped":
            # No direct equivalent, 'always' is closest if container is manually stopped then it stays stopped by systemd
            # until explicitly started again. 'on-failure' might be safer.
             container_unit.add_entry("Container", "Restart", "on-failure") # Or 'always'
        # 'no' is default (no restart)

    # --- Placeholder for add_*.sh logic ---
    # These functions will be called here or after initial unit creation
    # apply_network_config(container_unit, compose_service_config, all_compose_config, auxiliary_units)
    # apply_volume_config(container_unit, compose_service_config, all_compose_config, auxiliary_units)
    # apply_secret_config(container_unit, compose_service_config)
    # apply_autoupdate_labels(container_unit)
    # apply_oneshot_config(container_unit, compose_service_config)
    # apply_partof_config(container_unit, compose_service_config) # This might be on a .service wrapper

    # Add common autoupdate label
    container_unit.add_entry("Container", "Label", "io.containers.autoupdate=image")

    # Handle 'cap_add' and 'security_opt' (simplified)
    if 'cap_add' in compose_service_config:
        for cap in compose_service_config['cap_add']:
            container_unit.add_entry("Container", "PodmanArgs", f"--cap-add={cap}")

    if 'security_opt' in compose_service_config:
        for opt in compose_service_config['security_opt']:
            container_unit.add_entry("Container", "PodmanArgs", f"--security-opt={opt}")

    # Handle 'secrets' (Podman specific via Secret=)
    # Assumes secrets are already created in Podman by refresh_podman_secrets.sh
    if 'secrets' in compose_service_config:
        for secret_entry in compose_service_config['secrets']:
            secret_name = ""
            target_path = "" # For Quadlet, target is often same as source name if not specified
            if isinstance(secret_entry, str): # Simple form: "mysecret"
                secret_name = secret_entry
                target_path = secret_name # Or some default path convention if needed
            elif isinstance(secret_entry, dict): # Long form: {source: mysecret, target: /path/in/container}
                secret_name = secret_entry.get('source')
                target_path = secret_entry.get('target', secret_name) # If target is omitted, it's often the secret name itself

            if secret_name:
                # Quadlet format: Secret=mysecret[,target=/path/in/container]
                secret_quadlet_value = secret_name
                if target_path and target_path != secret_name : # Only add target if different and specified
                     # Quadlet usually expects target to be a filename if source is a secret name.
                     # If target is a dir, it might need different handling or podman args.
                     # For simplicity, let's assume target is the name it will have in the default secrets dir (/run/secrets)
                     # Or if an absolute path is given for target, that's more direct.
                     # This might need refinement based on how add_secrets_to_env.sh worked.
                     # If it was about env vars: Environment=MY_VAR=secret:mysecret
                    pass # Current add_secrets_to_env.sh likely does more, this is a placeholder
                    # For now, let's assume `add_secrets_to_env.sh` logic is complex and will be
                    # a separate function that modifies the container_unit or adds Env variables.
                    # This is a placeholder for direct Secret= mapping if that's desired.
                    # container_unit.add_entry("Container", "Secret", f"{secret_name},target={target_path}")

    # Handle 'sysctls' (simplified to PodmanArgs)
    if 'sysctls' in compose_service_config:
        sysctls = compose_service_config['sysctls']
        if isinstance(sysctls, dict):
            for key, value in sysctls.items():
                container_unit.add_entry("Container", "PodmanArgs", f"--sysctl={key}={value}")
        elif isinstance(sysctls, list): # list of "key=value"
            for item in sysctls:
                container_unit.add_entry("Container", "PodmanArgs", f"--sysctl={item}")


    # Handle 'volumes'
    if 'volumes' in compose_service_config:
        for vol_entry in compose_service_config['volumes']:
            if isinstance(vol_entry, str):
                parts = vol_entry.split(':')
                source = parts[0]
                target = parts[1] if len(parts) > 1 else None
                mode = parts[2] if len(parts) > 2 else None # ro, rw

                options = []
                if mode: options.append(mode)

                # Is it a host bind or a named volume?
                if source.startswith('/') or source.startswith('.'): # Likely a host path
                    container_unit.add_entry("Container", "Volume", f"{Path(source).resolve()}:{target}{(':' + ':'.join(options)) if options else ''}")
                else: # Named volume
                    # Check if this named volume is defined in the global 'volumes' section
                    is_globally_defined = source in all_compose_config.get('volumes', {})

                    # If not globally defined, or if defined but simple (no external settings),
                    # we might create a basic .volume file for it.
                    # For now, assume simple named volumes are handled by Podman or a basic .volume unit.
                    if not is_globally_defined:
                        vol_unit_name = sanitize_service_name_for_filename(f"{sane_service_name}-{source}-volume")
                        # Check if we already created such a volume unit for this service to avoid duplicates if referenced multiple times.
                        if not any(isinstance(u, VolumeUnit) and u.volume_name_on_host == source for u in auxiliary_units):
                            # Create a simple VolumeUnit. More complex definitions (driver, opts) would need parsing all_compose_config['volumes'][source]
                            simple_vol_unit = VolumeUnit(volume_name=source, service_name=vol_unit_name) # Name the .volume file uniquely
                            auxiliary_units.append(simple_vol_unit)

                    # Add to container unit
                    # Quadlet Volume=named_volume:/path/in/container[:options]
                    container_unit.add_entry("Container", "Volume", f"{source}:{target}{(':' + ':'.join(options)) if options else ''}")

            elif isinstance(vol_entry, dict): # Long syntax for volumes
                # source, target, type (volume, bind, tmpfs), readonly, etc.
                vol_type = vol_entry.get('type', 'volume')
                source = vol_entry.get('source')
                target = vol_entry.get('target')
                readonly = vol_entry.get('read_only', False)
                options = ['ro'] if readonly else ['rw'] # 'rw' is often default but can be explicit

                if not target: # Target is required
                    print(f"Warning: Volume entry for service '{service_name}' is missing 'target'. Skipping: {vol_entry}", flush=True)
                    continue

                if vol_type == 'bind':
                    if not source:
                        print(f"Warning: Bind mount for service '{service_name}' is missing 'source'. Skipping: {vol_entry}", flush=True)
                        continue
                    container_unit.add_entry("Container", "Volume", f"{Path(source).resolve()}:{target}{(':' + ':'.join(options)) if options else ''}")
                elif vol_type == 'volume':
                    if not source: # Anonymous volume, Podman handles this. Target path becomes the volume.
                         container_unit.add_entry("Container", "Volume", f"{target}{(':' + ':'.join(options)) if options else ''}")
                    else: # Named volume
                        is_globally_defined = source in all_compose_config.get('volumes', {})
                        if not is_globally_defined:
                            vol_unit_name = sanitize_service_name_for_filename(f"{sane_service_name}-{source}-volume")
                            if not any(isinstance(u, VolumeUnit) and u.volume_name_on_host == source for u in auxiliary_units):
                                simple_vol_unit = VolumeUnit(volume_name=source, service_name=vol_unit_name)
                                auxiliary_units.append(simple_vol_unit)
                        container_unit.add_entry("Container", "Volume", f"{source}:{target}{(':' + ':'.join(options)) if options else ''}")
                elif vol_type == 'tmpfs':
                     # Quadlet uses Tmpfs= /path/in/container[:options]
                    tmpfs_opts = vol_entry.get('tmpfs', {}).get('size') # e.g. size: 100m
                    opt_str = f":size={tmpfs_opts}" if tmpfs_opts else ""
                    container_unit.add_entry("Container", "Tmpfs", f"{target}{opt_str}")
                else:
                    print(f"Warning: Unsupported volume type '{vol_type}' for service '{service_name}'. Skipping: {vol_entry}", flush=True)

    # Handle 'networks'
    # This is simplified. Assumes networks are either predefined or simple bridge networks.
    if 'networks' in compose_service_config:
        networks_to_join = []
        if isinstance(compose_service_config['networks'], list): # simple list of network names
            networks_to_join = compose_service_config['networks']
        elif isinstance(compose_service_config['networks'], dict): # dictionary form with aliases etc.
            networks_to_join = list(compose_service_config['networks'].keys())
            # TODO: Handle aliases, ipv4_address etc. from the dict values if needed via PodmanArgs
            # For now, just connect to the network by name.

        for net_name in networks_to_join:
            # Check if this network is defined in the global 'networks' section
            # If not globally defined, Quadlet might create a default bridge or we might need a .network file.
            # For now, we assume simple named networks. If it's not 'host' or 'none', add Network=
            if net_name.lower() == "host":
                container_unit.add_entry("Container", "Network", "host")
            elif net_name.lower() == "none":
                 container_unit.add_entry("Container", "Network", "none")
            else:
                container_unit.add_entry("Container", "Network", net_name)
                # Optionally, create a NetworkUnit if not globally defined in compose
                is_globally_defined = net_name in all_compose_config.get('networks', {})
                if not is_globally_defined:
                    net_unit_name = sanitize_service_name_for_filename(f"{sane_service_name}-{net_name}-network")
                    if not any(isinstance(u, NetworkUnit) and u.network_name_on_host == net_name for u in auxiliary_units):
                        simple_net_unit = NetworkUnit(network_name=net_name, service_name=net_unit_name)
                        # TODO: parse all_compose_config['networks'][net_name] for driver, options if it were globally defined
                        auxiliary_units.append(simple_net_unit)

    return container_unit, auxiliary_units


# --- Main Orchestration Function (to be called by Typer command) ---
def generate_all_quadlet_files(
    affected_services: List[str],
    services_dir_path: Path,
    output_dir_path: Path,
    meta_target_name: Optional[str] = None, # e.g., "all-containers.target"
    vars_json_string: Optional[str] = None # JSON string from GitHub vars
) -> bool:
    """
    Generates all necessary Quadlet files for the affected services.
    If meta_target_name is provided, services will be made PartOf= this target.
    vars_json_string provides global environment variables.
    Returns True on success, False on failure.
    """
    if not services_dir_path.is_dir():
        print(f"Error: Services directory '{services_dir_path}' does not exist.", flush=True)
        return False

    output_dir_path = Path(os.path.expanduser(str(output_dir_path))) # Expand ~
    output_dir_path.mkdir(parents=True, exist_ok=True)

    all_ok = True
    global_env_vars_dict: Optional[Dict[str, str]] = None
    if vars_json_string:
        try:
            global_env_vars_dict = yaml.safe_load(vars_json_string) # Using yaml.safe_load as it handles JSON too
            if not isinstance(global_env_vars_dict, dict):
                print(f"Warning: VARS_JSON parsed to non-dict type: {type(global_env_vars_dict)}. Ignoring global vars.", flush=True)
                global_env_vars_dict = None
        except yaml.YAMLError as e:
            print(f"Warning: Could not parse VARS_JSON string. Error: {e}. Ignoring global vars.", flush=True)
            global_env_vars_dict = None


    for service_name in affected_services:
        sane_service_name = sanitize_service_name_for_filename(service_name)
        service_compose_file = services_dir_path / service_name / f"{service_name}.compose.yml" # Common convention
        # Or look for any *.compose.yml or docker-compose.yml
        if not service_compose_file.is_file():
             service_compose_file = services_dir_path / service_name / "docker-compose.yml"
             if not service_compose_file.is_file():
                service_compose_file = next((services_dir_path / service_name).glob("*.compose.y*ml"), None)

        if not service_compose_file or not service_compose_file.is_file():
            print(f"Warning: No compose file found for service '{service_name}' in '{services_dir_path / service_name}'. Skipping.", flush=True)
            continue

        print(f"Processing service '{service_name}' from '{service_compose_file}'...", flush=True)

        # Clean up existing files for this service first
        for old_file in output_dir_path.glob(f"{sane_service_name}.*"):
            try:
                old_file.unlink()
                print(f"Removed old unit file: {old_file.name}", flush=True)
            except OSError as e:
                print(f"Error removing old unit file {old_file.name}: {e}", flush=True)
                all_ok = False

        compose_config = parse_compose_file(service_compose_file)
        if not compose_config or 'services' not in compose_config:
            print(f"Error: Invalid or empty compose file for service '{service_name}'. Skipping.", flush=True)
            all_ok = False
            continue

        # Assuming one primary service per <service_name>.compose.yml, matching the directory name
        # or taking the first service if multiple are defined (less ideal).
        # A better approach might be to iterate if multiple services are in one file,
        # but current bash scripts seem to imply one service definition per directory.
        primary_compose_service_name = service_name # Assume compose service name matches directory name
        if primary_compose_service_name not in compose_config['services']:
            # Fallback: try to find if there's a service with the same name as the file (without .compose.yml)
            # Or just take the first service defined in the YAML.
            available_yaml_services = list(compose_config['services'].keys())
            if not available_yaml_services:
                print(f"Error: No services defined in compose file '{service_compose_file}'. Skipping.", flush=True)
                all_ok = False
                continue
            if service_name in available_yaml_services: # If a service is named like the folder
                primary_compose_service_name = service_name
            else: # Take the first one
                primary_compose_service_name = available_yaml_services[0]
                print(f"Warning: Service name '{service_name}' (from dir) not found in its compose file. Using first service found: '{primary_compose_service_name}'.", flush=True)

        compose_service_def = compose_config['services'][primary_compose_service_name]

        container_unit, aux_units = convert_compose_service_to_container_unit(
            service_name, # Use the directory name as the logical service name
            compose_service_def,
            compose_config,
            global_env_vars=global_env_vars_dict
        )

        units_to_write: List[QuadletUnit] = []
        if container_unit:
            units_to_write.append(container_unit)
        units_to_write.extend(aux_units)

        if not units_to_write:
            print(f"No units generated for service '{service_name}'.", flush=True)
            # all_ok = False # Not necessarily an error if a service is e.g. just a build context
            continue

        for unit in units_to_write:
            file_content = unit.generate_file_content()
            output_file_path = output_dir_path / unit.get_filename()
            try:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    f.write(file_content)
                print(f"Generated unit file: {output_file_path.name}", flush=True)
            except IOError as e:
                print(f"Error writing unit file {output_file_path.name}: {e}", flush=True)
                all_ok = False

        # After generating the primary .container file, create a .service file
        # that simply refers to it, if one doesn't exist or needs update.
        # This .service file is where systemd dependencies (Requires, After, PartOf) go.
        service_unit_file = output_dir_path / f"{sane_service_name}.service"
        if container_unit: # Only if a container was actually generated
            service_unit_content = f"""[Unit]
Description=Service for {sane_service_name} container
"""
            # Create a QuadletUnit for the .service file to manage its content
            service_unit_wrapper = QuadletUnit("service", sane_service_name)
            service_unit_wrapper.add_entry("Unit", "Description", f"Service for {sane_service_name} container")

            # DefaultDependencies for .service can be true, unlike .container
            # service_unit_wrapper.add_entry("Unit", "DefaultDependencies", "true")


            # Handle depends_on for Requires/After
            if 'depends_on' in compose_service_def:
                dependencies = compose_service_def['depends_on']
                # depends_on can be a list or a dictionary (for conditions)
                dep_names = []
                if isinstance(dependencies, list):
                    dep_names = dependencies
                elif isinstance(dependencies, dict):
                    dep_names = list(dependencies.keys()) # Basic: just use service names
                    # TODO: Handle conditions like service_healthy, service_started if needed

                for dep_name in dep_names:
                    sane_dep_name = sanitize_service_name_for_filename(dep_name)
                    service_unit_wrapper.add_entry("Unit", "Requires", f"{sane_dep_name}.service")
                    service_unit_wrapper.add_entry("Unit", "After", f"{sane_dep_name}.service")
                    # PartOf is often used for grouping and ensuring dependent services are stopped/started together
                    # For a typical "all services" meta-service (e.g. all-containers.target or similar)
                    # we would add PartOf=all-containers.target here.
                    # The original add_partof_services.sh might have specific logic for this.
                    # For now, let's assume a general PartOf= default.target or a passed-in meta target.
                    # This needs to align with how generate_meta_services.sh works.
                    # Let's assume for now that PartOf is handled by a dedicated function or step,
                    # as it might involve a meta-service that isn't known at this individual service level.


            # Determine container name for ExecStart/Stop
            # Try to find a --name arg in PodmanArgs
            podman_args_list = container_unit.sections.get("Container", {}).get("PodmanArgs", [])
            container_exec_name = sane_service_name # Default
            if isinstance(podman_args_list, str): # If it became a single string somehow
                podman_args_list = [podman_args_list]

            for arg in podman_args_list:
                if arg.startswith("--name="):
                    container_exec_name = arg.split('=', 1)[1]
                    break

            service_unit_wrapper.add_entry("Service", "ExecStart", f"/usr/bin/podman start {container_exec_name}")
            service_unit_wrapper.add_entry("Service", "ExecStop", f"/usr/bin/podman stop -t 10 {container_exec_name}")
            service_unit_wrapper.add_entry("Service", "KillMode", "mixed")

            # Handle Type (oneshot or typical service)
            # This is where add_oneshot_services.sh logic would come in.
            # Let's assume a compose label like 'com.example.systemd.type=oneshot'
            service_type = "forking" # Default for podman start/stop
            remain_after_exit = "yes"
            if compose_service_def.get('labels', {}).get('com.centOS.systemd.type', '').lower() == 'oneshot' or \
               compose_service_def.get('labels', {}).get('com.example.systemd.type', '').lower() == 'oneshot': # Example label
                service_type = "oneshot"
                remain_after_exit = "no" # Typically 'no' for oneshot unless it's setting up something persistent
                # For oneshot, ExecStart might be different (e.g. podman run --rm ... for a task)
                # This simplistic conversion assumes podman start is still okay for a oneshot if it's a pre-existing container
                # that does its job and exits. A true oneshot might be `podman run --rm ...` in ExecStart.
                # The current bash scripts likely handle this more specifically.
                # For now, we just change Type and RemainAfterExit.

            service_unit_wrapper.add_entry("Service", "Type", service_type)

            if service_type == "oneshot":
                # For oneshot, ExecStart should be 'podman run --rm ...'
                # This requires reconstructing the podman run arguments from the ContainerUnit.
                # This is a simplified version. A full version would need to translate all relevant
                # Container section keys (Image, Volume, Network, Env, Secret, PodmanArgs) into a podman run command.
                image_name = container_unit.sections.get("Container", {}).get("Image")
                if image_name:
                    # Basic podman run command. Needs to add volumes, envs, networks etc.
                    # This is a complex task to accurately rebuild from ContainerUnit fields.
                    # For a true oneshot, the original add_oneshot_services.sh might have had specific conventions.
                    # Let's build a more comprehensive run command.
                    podman_run_cmd_parts = ["/usr/bin/podman", "run", "--rm"]

                    # Name (usually for long-running, but can be useful for logs of oneshot)
                    if container_exec_name != sane_service_name: # if a custom name was set
                        podman_run_cmd_parts.append(f"--name={container_exec_name}")
                    else: # Use a unique name for the run to avoid clashes if not cleaned up, though --rm helps
                        podman_run_cmd_parts.append(f"--name={sane_service_name}-oneshot-$(uuidgen --random)")


                    # Environment Variables
                    env_vars = container_unit.sections.get("Container", {}).get("Environment", [])
                    if isinstance(env_vars, str): env_vars = [env_vars]
                    for env_var in env_vars:
                        podman_run_cmd_parts.extend(["--env", env_var])

                    # Secrets (as environment variables for simplicity if not using file mounts)
                    # This assumes secrets are available as env vars like MY_SECRET=secret:actual_secret
                    # If Secret= directive was used for file mounts, that's different.
                    # This part needs to align with how apply_secret_injection works.
                    # If apply_secret_injection already set up Secret= directives, then
                    # for a oneshot, those secrets would be mounted if we used 'podman start'.
                    # If we use 'podman run', we need to ensure the secret files are mounted
                    # or environment variables are passed.
                    # For now, this example assumes env var secrets are already in the Environment list.

                    # Volumes
                    volumes = container_unit.sections.get("Container", {}).get("Volume", [])
                    if isinstance(volumes, str): volumes = [volumes]
                    for vol in volumes:
                        podman_run_cmd_parts.extend(["--volume", vol])

                    # Networks
                    # Podman run uses --network. If multiple Network= lines, how to translate?
                    # Typically, a container joins networks listed.
                    # For simplicity, if a specific network other than host/none is set, use it.
                    networks = container_unit.sections.get("Container", {}).get("Network", [])
                    if isinstance(networks, str): networks = [networks]
                    for net in networks:
                        if net not in ["host", "none", "bridge", "private"]: # Default podman networks
                             podman_run_cmd_parts.extend(["--network", net])
                        elif net in ["host", "none"]:
                             podman_run_cmd_parts.extend([f"--network={net}"])


                    # Other PodmanArgs (excluding --name as it's handled)
                    raw_podman_args = container_unit.sections.get("Container", {}).get("PodmanArgs", [])
                    if isinstance(raw_podman_args, str): raw_podman_args = [raw_podman_args]
                    for arg in raw_podman_args:
                        if not arg.startswith("--name="):
                            podman_run_cmd_parts.append(arg)

                    podman_run_cmd_parts.append(image_name)

                    # Command / Entrypoint from compose (if any)
                    # TODO: Add compose_service_def.get('command') and compose_service_def.get('entrypoint')

                    service_unit_wrapper.add_entry("Service", "ExecStart", " ".join(podman_run_cmd_parts))
                else:
                    print(f"Warning: Oneshot service '{sane_service_name}' has no image defined. Cannot generate podman run command.", flush=True)
                    service_unit_wrapper.add_entry("Service", "ExecStart", f"/bin/false # Image missing for oneshot {sane_service_name}")

                # Oneshot services typically don't remain after exit unless they are setting up something.
                # And they usually don't have an ExecStop unless it's for cleanup.
                service_unit_wrapper.sections["Service"].pop("ExecStop", None) # Remove default ExecStop
                service_unit_wrapper.sections["Service"].pop("RemainAfterExit", None) # Remove default RemainAfterExit
            else: # Not oneshot
                 service_unit_wrapper.add_entry("Service", "RemainAfterExit", remain_after_exit)


            service_unit_wrapper.add_entry("Install", "WantedBy", "default.target")

            # Apply PartOf logic (simplified from add_partof_services.sh)
            # Assumes a convention: if a service is part of "default.target" (most are),
            # and if a specific meta-target like "all-containers.target" exists or is configured,
            # it should be part of that.
            # This could be passed as an argument or discovered.
            # For now, let's assume a global 'main_target' could be 'default.target' or a custom one.
            # The original add_partof_services.sh might have more complex logic to determine this.
            # A common pattern is to make services PartOf= a specific target that groups them.
            # If a global 'app_target_name' (e.g., "my-app.target") is provided, use it.
            # This is a placeholder for where that logic would integrate.
            # Example: if a global_meta_target = "all-containers.target" is passed to generate_all_quadlet_files:
            #   service_unit_wrapper.add_entry("Unit", "PartOf", global_meta_target)
            # This makes them stop when 'all-containers.target' stops.
            # Example: if a global_meta_target = "all-containers.target" is passed to generate_all_quadlet_files:
            #   service_unit_wrapper.add_entry("Unit", "PartOf", global_meta_target)
            # This is now handled by a parameter to generate_all_quadlet_files.
            if meta_target_name:
                service_unit_wrapper.add_entry("Unit", "PartOf", meta_target_name)

            from .secret_handler import apply_secret_injection # Import locally to avoid circular if moved
            # Secret handling: Replicating add_secrets_to_env.sh logic
            # This function will modify container_unit by adding Environment= or Secret= lines
            apply_secret_injection(container_unit, compose_service_def, all_compose_config)


            try:
                with open(service_unit_file, 'w', encoding='utf-8') as f:
                    f.write(service_unit_wrapper.generate_file_content())
                print(f"Generated service file: {service_unit_file.name}", flush=True)
            except IOError as e:
                print(f"Error writing service file {service_unit_file.name}: {e}", flush=True)
                all_ok = False

    return all_ok
