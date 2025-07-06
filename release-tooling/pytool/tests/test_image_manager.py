import pytest
import subprocess
from pathlib import Path
from unittest import mock

from release_tool import image_manager

@pytest.fixture
def mock_units_dir(tmp_path: Path) -> Path:
    units_dir = tmp_path / "test_units"
    units_dir.mkdir()
    return units_dir

# --- Tests for get_image_from_container_file ---

def test_get_image_from_container_file_success(mock_units_dir: Path):
    container_file = mock_units_dir / "service_a.container"
    container_file.write_text("[Unit]\nDescription=Test\n[Container]\nImage=myimage:latest\nExec=sleep inf")

    image = image_manager.get_image_from_container_file(container_file)
    assert image == "myimage:latest"

def test_get_image_from_container_file_no_image_key(mock_units_dir: Path):
    container_file = mock_units_dir / "service_b.container"
    container_file.write_text("[Unit]\nDescription=Test\n[Container]\nExec=sleep inf")

    image = image_manager.get_image_from_container_file(container_file)
    assert image is None

def test_get_image_from_container_file_empty_file(mock_units_dir: Path):
    container_file = mock_units_dir / "service_c.container"
    container_file.write_text("")
    image = image_manager.get_image_from_container_file(container_file)
    assert image is None

def test_get_image_from_container_file_not_found(mock_units_dir: Path):
    container_file = mock_units_dir / "nonexistent.container"
    image = image_manager.get_image_from_container_file(container_file)
    assert image is None

def test_get_image_from_container_file_malformed(mock_units_dir: Path):
    container_file = mock_units_dir / "service_d.container"
    container_file.write_text("[Container\nImage=foo") # Malformed line
    image = image_manager.get_image_from_container_file(container_file)
    assert image is None # Or check for logged error if capsys is used

# --- Tests for pull_image ---

@mock.patch("subprocess.run")
def test_pull_image_success(mock_subprocess_run: mock.MagicMock):
    mock_subprocess_run.return_value = subprocess.CompletedProcess(args=["podman", "pull", "myimage:v1"], returncode=0, stdout="Pulled.", stderr="")

    assert image_manager.pull_image("myimage:v1") is True
    mock_subprocess_run.assert_called_once_with(["podman", "pull", "myimage:v1"], capture_output=True, text=True, check=False)

@mock.patch("subprocess.run")
def test_pull_image_failure(mock_subprocess_run: mock.MagicMock):
    mock_subprocess_run.return_value = subprocess.CompletedProcess(args=["podman", "pull", "myimage:v2"], returncode=1, stdout="", stderr="Not found.")

    assert image_manager.pull_image("myimage:v2") is False
    mock_subprocess_run.assert_called_once_with(["podman", "pull", "myimage:v2"], capture_output=True, text=True, check=False)

@mock.patch("subprocess.run", side_effect=FileNotFoundError("podman not found"))
def test_pull_image_podman_not_found(mock_subprocess_run: mock.MagicMock):
    assert image_manager.pull_image("myimage:v3") is False
    # Check that it was attempted to be called
    mock_subprocess_run.assert_called_once_with(["podman", "pull", "myimage:v3"], capture_output=True, text=True, check=False)


# --- Tests for pull_images_for_services ---

@mock.patch("release_tool.image_manager.pull_image")
@mock.patch("release_tool.image_manager.get_image_from_container_file")
def test_pull_images_for_services_all_success(
    mock_get_image: mock.MagicMock,
    mock_pull: mock.MagicMock,
    mock_units_dir: Path
):
    affected = ["svc1", "svc2"]
    # Mock get_image_from_container_file behavior
    mock_get_image.side_effect = lambda filepath: {
        mock_units_dir / "svc1.container": "image1:latest",
        mock_units_dir / "svc2.container": "image2:tag",
    }.get(filepath)
    # Mock pull_image behavior
    mock_pull.return_value = True # All pulls succeed

    assert image_manager.pull_images_for_services(affected, mock_units_dir) is True
    assert mock_get_image.call_count == 2
    mock_get_image.assert_any_call(mock_units_dir / "svc1.container")
    mock_get_image.assert_any_call(mock_units_dir / "svc2.container")
    assert mock_pull.call_count == 2
    mock_pull.assert_any_call("image1:latest")
    mock_pull.assert_any_call("image2:tag")

@mock.patch("release_tool.image_manager.pull_image")
@mock.patch("release_tool.image_manager.get_image_from_container_file")
def test_pull_images_for_services_one_fails(
    mock_get_image: mock.MagicMock,
    mock_pull: mock.MagicMock,
    mock_units_dir: Path
):
    affected = ["svc1", "svc2"]
    mock_get_image.side_effect = lambda filepath: {
        mock_units_dir / "svc1.container": "image1:latest",
        mock_units_dir / "svc2.container": "image2:tag",
    }.get(filepath)
    # svc1 pull succeeds, svc2 pull fails
    mock_pull.side_effect = lambda imagename: True if imagename == "image1:latest" else False

    assert image_manager.pull_images_for_services(affected, mock_units_dir) is False
    assert mock_pull.call_count == 2
    mock_pull.assert_any_call("image1:latest")
    mock_pull.assert_any_call("image2:tag")


def test_pull_images_for_services_no_services(mock_units_dir: Path):
    assert image_manager.pull_images_for_services([], mock_units_dir) is True

def test_pull_images_for_services_units_dir_missing(tmp_path: Path):
    assert image_manager.pull_images_for_services(["svc1"], tmp_path / "non_existent_units") is False

@mock.patch("release_tool.image_manager.pull_image") # Still mock pull_image to avoid actual calls
@mock.patch("release_tool.image_manager.get_image_from_container_file", return_value=None)
def test_pull_images_for_services_no_image_in_file(
    mock_get_image: mock.MagicMock,
    mock_pull: mock.MagicMock,
    mock_units_dir: Path
):
    affected = ["svc_no_image"]
    # get_image_from_container_file will return None for svc_no_image.container

    # This behavior (returning True if no image is found) matches the original script's non-strictness.
    # A stricter version might return False here.
    assert image_manager.pull_images_for_services(affected, mock_units_dir) is True
    mock_get_image.assert_called_once_with(mock_units_dir / "svc_no_image.container")
    mock_pull.assert_not_called() # pull_image should not be called if no image string is found

@mock.patch("release_tool.image_manager.pull_image") # Mock pull_image
@mock.patch("release_tool.image_manager.get_image_from_container_file")
def test_pull_images_for_services_mix_found_not_found(
    mock_get_image: mock.MagicMock,
    mock_pull: mock.MagicMock,
    mock_units_dir: Path
):
    affected = ["svc_alpha", "svc_beta"] # svc_alpha has image, svc_beta doesn't
    mock_get_image.side_effect = lambda filepath: "alpha_img:v1" if filepath == mock_units_dir / "svc_alpha.container" else None
    mock_pull.return_value = True # Assume pull succeeds for alpha_img

    assert image_manager.pull_images_for_services(affected, mock_units_dir) is True
    mock_get_image.assert_any_call(mock_units_dir / "svc_alpha.container")
    mock_get_image.assert_any_call(mock_units_dir / "svc_beta.container")
    mock_pull.assert_called_once_with("alpha_img:v1")
