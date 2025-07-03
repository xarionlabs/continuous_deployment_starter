# release_tool/secret_handler.py
from typing import Dict, Any
from .unit_generator import ContainerUnit # Use a forward reference if in the same file, or import

def apply_secret_injection(
    container_unit: ContainerUnit,
    compose_service_config: Dict[str, Any],
    all_compose_config: Dict[str, Any] # Full compose for context if needed (e.g. top-level secrets)
):
    """
    Processes the 'secrets' section from a Docker Compose service definition
    and adds appropriate 'Secret=' directives to the ContainerUnit.

    Assumes that the actual Podman secrets have been created by an earlier process
    (like the original refresh_podman_secrets.sh).
    """
    if 'secrets' not in compose_service_config:
        return

    # Check for top-level 'secrets' definitions in the compose file, which might define external secrets
    global_secrets_config = all_compose_config.get('secrets', {})

    for secret_entry in compose_service_config['secrets']:
        secret_name_in_compose = "" # Name used in the service's 'secrets' list
        podman_secret_name = ""   # Actual name of the secret in Podman's secret store
        target_in_container = ""  # Target path/filename inside the container
        # uid = None
        # gid = None
        # mode = None

        if isinstance(secret_entry, str): # Simple form: "my_secret_alias"
            secret_name_in_compose = secret_entry
            podman_secret_name = secret_name_in_compose # Assume alias is the podman secret name if not defined globally
            target_in_container = secret_name_in_compose # Default target is the secret name
        elif isinstance(secret_entry, dict): # Long form: {source: actual_podman_secret, target: /path/secret_file, ...}
            secret_name_in_compose = secret_entry.get('source')
            if not secret_name_in_compose:
                print(f"Warning: Secret entry for service '{container_unit.service_name}' is missing 'source'. Skipping: {secret_entry}", flush=True)
                continue
            podman_secret_name = secret_name_in_compose # Initially assume source is the podman secret name
            target_in_container = secret_entry.get('target', secret_name_in_compose) # Default target to source name
            # uid = secret_entry.get('uid')
            # gid = secret_entry.get('gid')
            # mode = secret_entry.get('mode') # e.g. '0400'
        else:
            print(f"Warning: Invalid secret entry format for service '{container_unit.service_name}'. Skipping: {secret_entry}", flush=True)
            continue

        # If the secret_name_in_compose refers to a top-level secret definition,
        # it might specify 'external: true' or a different 'name' for the actual Podman secret.
        if secret_name_in_compose in global_secrets_config:
            global_secret_def = global_secrets_config[secret_name_in_compose]
            if isinstance(global_secret_def, dict):
                if global_secret_def.get('external', False) and 'name' in global_secret_def:
                    # If external is true and a specific 'name' is given, that's the Podman secret name
                    podman_secret_name = global_secret_def['name']
                elif global_secret_def.get('external', False):
                    # External, but no specific name, so secret_name_in_compose is the Podman secret name
                    podman_secret_name = secret_name_in_compose
                elif 'file' in global_secret_def:
                    # Secret defined by a local file. This script isn't creating the Podman secret itself,
                    # so we assume 'refresh_podman_secrets.sh' would have handled this using 'secret_name_in_compose'
                    # as the Podman secret name.
                    podman_secret_name = secret_name_in_compose
                elif 'name' in global_secret_def: # Not external, but has a custom name for the Podman secret
                    podman_secret_name = global_secret_def['name']


        if not podman_secret_name:
            print(f"Warning: Could not determine Podman secret name for compose secret '{secret_name_in_compose}' in service '{container_unit.service_name}'. Skipping.", flush=True)
            continue

        # Construct the Quadlet Secret= value
        # Format: Secret=mysecret[,target=targetname][,uid=val][,gid=val][,mode=val]
        secret_directive_value = podman_secret_name
        options = []
        if target_in_container and target_in_container != podman_secret_name: # Only add if target is different & specified
            options.append(f"target={target_in_container}")
        # if uid is not None: options.append(f"uid={uid}")
        # if gid is not None: options.append(f"gid={gid}")
        # if mode is not None: options.append(f"mode={mode}")

        if options:
            secret_directive_value += f",{','.join(options)}"

        container_unit.add_entry("Container", "Secret", secret_directive_value)
        print(f"Info: Added Secret='{secret_directive_value}' for service '{container_unit.service_name}'", flush=True)

    # What about Environment=MY_VAR=secret:some_podman_secret ?
    # The original add_secrets_to_env.sh might have preferred this for some cases.
    # This would require parsing compose 'environment' variables that might have a special format
    # indicating they should be sourced from a Podman secret.
    # For now, this function only handles the 'secrets:' block of a compose service.
    # If environment variables need to be populated from secrets, that should be a separate
    # transformation on the 'environment' block, potentially using this kind of syntax.
    # Example:
    # environment:
    #   API_KEY: secret:my_api_key_secret # This would become Environment=API_KEY=secret:my_api_key_secret
    # This is NOT implemented here yet.
    pass
