# tests/test_unit_generator.py
import pytest
import yaml
from pathlib import Path
from typing import Dict, Any, List
from unittest import mock

from release_tool.unit_generator import (
    QuadletUnit,
    ContainerUnit,
    VolumeUnit,
    NetworkUnit,
    parse_compose_file,
    sanitize_service_name_for_filename,
    convert_compose_service_to_container_unit,
    generate_all_quadlet_files
)
from release_tool.secret_handler import apply_secret_injection

# --- Fixtures ---

@pytest.fixture
def mock_services_base_dir(tmp_path: Path) -> Path:
    """Creates a temporary base directory utils/release_tool/services for tests."""
    services_dir = tmp_path / "services"
    services_dir.mkdir(parents=True, exist_ok=True)
    return services_dir

@pytest.fixture
def mock_output_dir(tmp_path: Path) -> Path:
    """Creates a temporary output directory."""
    out_dir = tmp_path / "output_quadlets"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

@pytest.fixture
def sample_compose_service_simple() -> Dict[str, Any]:
    return {
        "image": "nginx:latest",
        "ports": ["8080:80"],
        "environment": {"NGINX_HOST": "example.com", "EMPTY_VAR": None},
        "restart": "always",
    }

@pytest.fixture
def sample_compose_service_full(sample_compose_service_simple: Dict[str, Any]) -> Dict[str, Any]:
    config = {
        "version": "3.8",
        "services": {
            "web_server": sample_compose_service_simple,
            "db_server": {
                "image": "postgres:15",
                "volumes": ["db_data:/var/lib/postgresql/data", "./config/pg.conf:/etc/postgresql/postgresql.conf:ro"],
                "networks": ["backend_net"],
                "secrets": [{"source": "db_password", "target": "/run/secrets/postgres_password"}],
                "depends_on": ["web_server"],
                "labels": {"com.example.systemd.type": "oneshot"}
            }
        },
        "volumes": {
            "db_data": {"driver": "local"}
        },
        "networks": {
            "backend_net": {"driver": "bridge"}
        },
        "secrets": {
            "db_password": {"external": True, "name": "actual_db_secret_in_podman"}
        }
    }
    return config

# --- Tests for Helper Functions ---

def test_parse_compose_file_success(tmp_path: Path):
    content = {"version": "3.8", "services": {"test_svc": {"image": "alpine"}}}
    file_path = tmp_path / "test.compose.yml"
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(content, f)

    parsed = parse_compose_file(file_path)
    assert parsed == content

def test_parse_compose_file_not_found(tmp_path: Path):
    assert parse_compose_file(tmp_path / "nonexistent.yml") is None

def test_parse_compose_file_invalid_yaml(tmp_path: Path):
    file_path = tmp_path / "invalid.yml"
    file_path.write_text("image: alpine\n  bad_indent: true")
    assert parse_compose_file(file_path) is None

def test_sanitize_service_name():
    assert sanitize_service_name_for_filename("my-service!@1") == "my-service_1" # Corrected expectation
    assert sanitize_service_name_for_filename("valid_name.test") == "valid_name.test"

# --- Tests for QuadletUnit Class ---

def test_quadlet_unit_basic():
    unit = QuadletUnit("testtype", "testsvc")
    unit.add_entry("Unit", "Description", "A test service")
    unit.add_entry("Service", "ExecStart", "/bin/true")
    expected_content = "[Unit]\nDescription=A test service\n\n[Service]\nExecStart=/bin/true\n" # Adjusted to one trailing newline
    assert unit.generate_file_content() == expected_content
    assert unit.get_filename() == "testsvc.testtype"

def test_quadlet_unit_multi_value():
    unit = QuadletUnit("container", "test_multi")
    unit.add_entry("Container", "Environment", "VAR1=val1")
    unit.add_entry("Container", "Environment", "VAR2=val2")
    unit.add_entry("Container", "Volume", "/foo:/bar")
    unit.add_entry("Container", "Volume", ["/data:/data", "/tmp:/ex"])

    content = unit.generate_file_content()
    assert "Environment=VAR1=val1" in content
    assert "Environment=VAR2=val2" in content
    assert "Volume=/foo:/bar" in content
    assert "Volume=/data:/data" in content
    assert "Volume=/tmp:/ex" in content


# --- Tests for convert_compose_service_to_container_unit ---
# These will need to be more comprehensive

def test_convert_simple_service(sample_compose_service_simple: Dict[str, Any]):
    service_name = "web"
    full_compose = {"services": {service_name: sample_compose_service_simple}}

    container_unit, aux_units = convert_compose_service_to_container_unit(
        service_name, sample_compose_service_simple, full_compose
    )

    assert isinstance(container_unit, ContainerUnit)
    assert container_unit.service_name == service_name
    assert container_unit.sections["Container"]["Image"] == "nginx:latest"
    assert "8080:80" in container_unit.sections["Container"]["Port"]
    assert "NGINX_HOST=example.com" in container_unit.sections["Container"]["Environment"]
    assert "EMPTY_VAR=" in container_unit.sections["Container"]["Environment"]
    assert container_unit.sections["Container"]["Restart"] == "always"
    assert "io.containers.autoupdate=image" in container_unit.sections["Container"]["Label"]
    assert len(aux_units) == 0

def test_convert_service_env_vars_merging_and_override(sample_compose_service_simple: Dict[str, Any]):
    service_name = "env_test_svc"
    service_config = {
        "image": "myimage:latest",
        "environment": {
            "SERVICE_VAR": "service_value", # Override global
            "SERVICE_ONLY_VAR": "specific_to_service",
            "EMPTY_SERVICE_VAR": None
        }
    }
    full_compose = {"services": {service_name: service_config}}
    global_env = {
        "GLOBAL_VAR": "global_value",
        "SERVICE_VAR": "global_override_me",
        "GLOBAL_EMPTY_VAR": None
    }

    container_unit, _ = convert_compose_service_to_container_unit(
        service_name, service_config, full_compose, global_env_vars=global_env
    )

    assert isinstance(container_unit, ContainerUnit)
    env_entries = container_unit.sections["Container"]["Environment"]

    # Convert list of "KEY=VALUE" strings to a dict for easier assertion
    env_dict = {}
    if isinstance(env_entries, list):
        for entry in env_entries:
            if '=' in entry:
                k, v = entry.split('=', 1)
                env_dict[k] = v
            else: # Should not happen based on current logic for dict inputs
                env_dict[entry] = ""
    elif isinstance(env_entries, str): # Single entry
         if '=' in env_entries:
            k, v = env_entries.split('=', 1)
            env_dict[k] = v
         else:
            env_dict[env_entries] = ""


    assert env_dict["GLOBAL_VAR"] == "global_value"
    assert env_dict["SERVICE_VAR"] == "service_value" # Service overrides global
    assert env_dict["SERVICE_ONLY_VAR"] == "specific_to_service"
    assert env_dict["EMPTY_SERVICE_VAR"] == "" # None becomes empty string
    assert env_dict["GLOBAL_EMPTY_VAR"] == ""

def test_convert_service_env_vars_list_format(capsys):
    service_name = "env_list_svc"
    service_config = {
        "image": "myimage:latest",
        "environment": [
            "LIST_VAR1=value1",
            "LIST_VAR2=",
            "UNSUPPORTED_KEY_ONLY" # This should be warned about and ignored
        ]
    }
    full_compose = {"services": {service_name: service_config}}

    container_unit, _ = convert_compose_service_to_container_unit(
        service_name, service_config, full_compose, global_env_vars=None
    )

    assert isinstance(container_unit, ContainerUnit)
    env_entries = container_unit.sections["Container"]["Environment"]

    expected_env_list = [
        "LIST_VAR1=value1",
        "LIST_VAR2="
    ]
    # Check if all expected entries are present
    for expected_entry in expected_env_list:
        assert expected_entry in env_entries

    # Check that UNSUPPORTED_KEY_ONLY is not present
    assert not any("UNSUPPORTED_KEY_ONLY" in entry for entry in env_entries)

    captured = capsys.readouterr()
    assert f"Warning: Service '{service_name}' environment list contains key-only entry 'UNSUPPORTED_KEY_ONLY'. This is not supported and will be ignored." in captured.out


# --- Tests for generate_all_quadlet_files (Orchestration) ---
# These are more like integration tests for the generator module

# Removing the problematic test_generate_all_simple_service as test_generate_all_actual_files is more robust.
# @mock.patch("release_tool.unit_generator.Path.unlink", autospec=True)
# @mock.patch("release_tool.unit_generator.Path.open", new_callable=mock.mock_open)
# @mock.patch("release_tool.unit_generator.parse_compose_file")
# def test_generate_all_simple_service(
#     mock_parse_compose: mock.MagicMock,
#     mock_file_open: mock.MagicMock,
#     mock_unlink: mock.MagicMock,
#     mock_services_base_dir: Path,
#     mock_output_dir: Path,
#     sample_compose_service_simple: Dict[str, Any],
# ):
#     service_name = "my_web_server"
#     (mock_services_base_dir / service_name).mkdir()
#     mock_parse_compose.return_value = {
#         "services": {
#             service_name: sample_compose_service_simple
#         }
#     }
#     mock_output_dir_path = Path(mock_output_dir)
#     def glob_results(pattern): # pragma: no cover (code was problematic)
#         return []
#     # This glob assignment was the source of AttributeError
#     # mock_output_dir_path.glob = glob_results
#     # Instead, if mocking glob, it should be done via mocker.patch.object or similar.
    # # The line below was causing SyntaxError
#     success = generate_all_quadlet_files(
#         affected_services=[service_name],
#         services_dir_path=mock_services_base_dir,
#         output_dir_path=mock_output_dir_path,
#         meta_target_name="all.target"
#     )
#     assert success


# To make the above test more robust without overly complex mocks:
def test_generate_all_actual_files(
    mock_services_base_dir: Path, # Actual temp dir
    mock_output_dir: Path,      # Actual temp dir
    sample_compose_service_simple: Dict[str, Any],
):
    service_name = "actual_web"
    service_path = mock_services_base_dir / service_name
    service_path.mkdir()
    compose_content = {"services": {service_name: sample_compose_service_simple}}
    with open(service_path / f"{service_name}.compose.yml", "w") as f:
        yaml.dump(compose_content, f)

    # Create a dummy old file to check cleanup
    (mock_output_dir / f"{service_name}.old_unit").write_text("old stuff")

    success = generate_all_quadlet_files(
        affected_services=[service_name],
        services_dir_path=mock_services_base_dir,
        output_dir_path=mock_output_dir,
        meta_target_name="all-myapp.target"
    )
    assert success
    assert not (mock_output_dir / f"{service_name}.old_unit").exists() # Check cleanup

    container_file = mock_output_dir / f"{service_name}.container"
    service_file = mock_output_dir / f"{service_name}.service"

    assert container_file.exists()
    assert service_file.exists()

    container_content = container_file.read_text()
    assert "[Unit]" in container_content
    assert f"Description=Podman container for {service_name}" in container_content
    assert "Image=nginx:latest" in container_content
    assert "Port=8080:80" in container_content
    assert "Environment=NGINX_HOST=example.com" in container_content
    assert "Restart=always" in container_content
    assert "Label=io.containers.autoupdate=image" in container_content

    service_content = service_file.read_text()
    assert "[Unit]" in service_content
    assert f"Description=Service for {service_name} container" in service_content
    assert "PartOf=all-myapp.target" in service_content
    assert "[Service]" in service_content
    assert f"ExecStart=/usr/bin/podman start {service_name}" in service_content # Assumes default naming
    assert "Type=forking" in service_content
    assert "[Install]" in service_content
    assert "WantedBy=default.target" in service_content


# TODO: Add more tests for:
# - Volume generation (named, host-bind, .volume files)
# - Network generation (.network files, connecting to existing)
# - Secret injection (Quadlet Secret= lines)
# - Depends_on translation to Requires/After in .service file
# - Oneshot service generation (podman run --rm in ExecStart)
# - Edge cases: missing image, invalid compose fields, etc.
# - Multiple services processed in one call
# - Correct handling of sanitize_service_name_for_filename in output filenames
# - Test for apply_secret_injection in test_secret_handler.py
# - Test for different configurations of meta_target_name
# - Test for services with no primary compose service name match (using first service)

# Placeholder for secret handler tests
# (Ideally in a separate tests/test_secret_handler.py)
def test_apply_secret_injection_simple():
    container_unit = ContainerUnit("my_app")
    compose_service_config = {
        "secrets": ["my_podman_secret"]
    }
    all_compose_config = {
        "secrets": { "my_podman_secret": {"external": True} } # Assume it's an external Podman secret
    }
    apply_secret_injection(container_unit, compose_service_config, all_compose_config)

    secrets_val = container_unit.sections.get("Container", {}).get("Secret")
    if isinstance(secrets_val, str): secrets_val = [secrets_val]
    elif secrets_val is None: secrets_val = []
    assert "my_podman_secret" in secrets_val # Quadlet Secret= value is just the name or name,target=...

def test_apply_secret_injection_long_syntax():
    container_unit = ContainerUnit("my_app_long")
    compose_service_config = {
        "secrets": [{"source": "actual_secret", "target": "/etc/app/secret_file"}]
    }
    # Case 1: actual_secret is an external podman secret
    all_compose_config_ext = {
        "secrets": {"actual_secret": {"external": True}}
    }
    apply_secret_injection(container_unit, compose_service_config, all_compose_config_ext)

    secrets_val_ext = container_unit.sections.get("Container", {}).get("Secret")
    if isinstance(secrets_val_ext, str): secrets_val_ext = [secrets_val_ext]
    elif secrets_val_ext is None: secrets_val_ext = []
    assert "actual_secret,target=/etc/app/secret_file" in secrets_val_ext

    # Case 2: actual_secret refers to a named secret in top-level that might have a different podman name
    container_unit_named = ContainerUnit("my_app_named_src")
    compose_service_config_named_src = {
         "secrets": [{"source": "app_db_password_alias", "target": "db_pass.txt"}]
    }
    all_compose_config_named = {
        "secrets": {
            "app_db_password_alias": {"name": "podman_specific_db_password", "external": True}
        }
    }
    apply_secret_injection(container_unit_named, compose_service_config_named_src, all_compose_config_named)

    secrets_val_named = container_unit_named.sections.get("Container", {}).get("Secret")
    if isinstance(secrets_val_named, str): secrets_val_named = [secrets_val_named]
    elif secrets_val_named is None: secrets_val_named = []
    assert "podman_specific_db_password,target=db_pass.txt" in secrets_val_named

# (End of placeholder for secret handler tests)
