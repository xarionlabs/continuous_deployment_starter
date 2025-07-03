# tests/test_changed_services.py
import pytest
from pathlib import Path
from typing import List, Set

from release_tool import changed_services

# Define a common set of critical patterns for tests, mirroring the defaults
# This makes tests less reliant on the exact global definition if it were to change
# for reasons not relevant to the test itself.
TEST_CRITICAL_PATTERNS = [
    ".github/workflows/scripts/generate_quadlets.sh", # Example critical script
    ".github/workflows/release.yml" # Example critical workflow
]

@pytest.fixture
def mock_services_dir(tmp_path: Path) -> Path:
    """Creates a temporary services directory with some dummy service subdirectories."""
    services_base = tmp_path / "services"
    services_base.mkdir()
    (services_base / "service_a").mkdir()
    (services_base / "service_b").mkdir()
    (services_base / "service_c").mkdir()
    return services_base

def test_get_all_services(mock_services_dir: Path):
    expected_services = {"service_a", "service_b", "service_c"}
    assert changed_services.get_all_services(mock_services_dir) == expected_services

def test_get_all_services_empty(tmp_path: Path):
    empty_services_dir = tmp_path / "empty_services"
    empty_services_dir.mkdir()
    assert changed_services.get_all_services(empty_services_dir) == set()

def test_get_all_services_non_existent(tmp_path: Path):
    non_existent_dir = tmp_path / "non_existent"
    # We expect it to print a warning (captured by pytest if using capsys) and return empty set
    assert changed_services.get_all_services(non_existent_dir) == set()


@pytest.mark.parametrize(
    "changed_files_str, assume_value_changes, expected_output_list, description",
    [
        # Scenario 1: No changes, no assume_value_changes
        ("", False, [], "No changes, no assume flag"),
        # Scenario 2: No changes, assume_value_changes is True
        ("", True, ["service_a", "service_b", "service_c"], "No changes, assume flag true -> all services"),
        # Scenario 3: Change in a single service file
        ("services/service_a/file.txt", False, ["service_a"], "Single service file change"),
        # Scenario 4: Changes in multiple service files
        ("services/service_a/file.txt services/service_b/another.yml", False, ["service_a", "service_b"], "Multiple service files change"),
        # Scenario 5: Change in a non-service file (should not affect services)
        ("other/docs/readme.md", False, [], "Non-service file change"),
        # Scenario 6: Change in a critical global script
        (".github/workflows/scripts/generate_quadlets.sh", False, ["service_a", "service_b", "service_c"], "Critical global script change -> all services"),
        # Scenario 7: Change in release.yml
        (".github/workflows/release.yml", False, ["service_a", "service_b", "service_c"], "release.yml change -> all services"),
        # Scenario 8: Mixed changes including a critical script
        ("services/service_a/file.txt .github/workflows/release.yml", False, ["service_a", "service_b", "service_c"], "Mixed with critical script -> all services"),
        # Scenario 9: Service file change AND assume_value_changes true (specific change takes precedence)
        ("services/service_b/config.json", True, ["service_b"], "Service change, assume flag true -> specific service"),
        # Scenario 10: Path normalization - leading ./
        ("./services/service_c/update.sh", False, ["service_c"], "Service file with leading ./"),
        # Scenario 11: Critical script with leading ./
        ("./.github/workflows/scripts/generate_quadlets.sh", False, ["service_a", "service_b", "service_c"], "Critical script with leading ./"),
        # Scenario 12: Change in a file within services/ but not a recognized service subdirectory
        ("services/unknown_service/data.db", False, [], "Change in unknown subdir under services/"),
        # Scenario 13: Multiple files, some relevant, some not
        ("services/service_a/x.py docs/file.md services/service_c/y.txt", False, ["service_a", "service_c"], "Multiple files, mixed relevance"),
        # Scenario 14: Empty string for changed_files but assume_value_changes is True
        (" ", True, ["service_a", "service_b", "service_c"], "Whitespace changed_files, assume_value_changes True"),
    ]
)
def test_determine_affected_services(
    mock_services_dir: Path,
    changed_files_str: str,
    assume_value_changes: bool,
    expected_output_list: List[str],
    description: str
):
    # Use the TEST_CRITICAL_PATTERNS for consistency in tests
    result = changed_services.determine_affected_services(
        changed_files_str=changed_files_str,
        assume_value_changes=assume_value_changes,
        services_dir=str(mock_services_dir),
        critical_patterns_override=TEST_CRITICAL_PATTERNS
    )
    assert sorted(result) == sorted(expected_output_list), f"Test failed for: {description}"

def test_determine_affected_services_no_services_dir(tmp_path: Path):
    """Test behavior when the services directory doesn't exist."""
    services_dir = tmp_path / "non_existent_services"
    result = changed_services.determine_affected_services(
        changed_files_str="services/service_a/file.txt",
        assume_value_changes=False,
        services_dir=str(services_dir),
        critical_patterns_override=TEST_CRITICAL_PATTERNS
    )
    assert result == [], "Should return empty list if services_dir does not exist"

def test_determine_affected_services_empty_services_dir(tmp_path: Path):
    """Test behavior when the services directory exists but is empty."""
    services_dir = tmp_path / "empty_services_dir"
    services_dir.mkdir()
    result = changed_services.determine_affected_services(
        changed_files_str="services/service_a/file.txt", # This service won't be "defined"
        assume_value_changes=False,
        services_dir=str(services_dir),
        critical_patterns_override=TEST_CRITICAL_PATTERNS
    )
    assert result == [], "Should return empty list if services_dir is empty"

    result_assume_true = changed_services.determine_affected_services(
        changed_files_str="",
        assume_value_changes=True, # This would normally trigger all, but there are no services
        services_dir=str(services_dir),
        critical_patterns_override=TEST_CRITICAL_PATTERNS
    )
    assert result_assume_true == [], "Should return empty list even with assume_value_changes if services_dir is empty"
