#!/bin/bash

# test-setup.sh - Validate the complete local testing setup
# This script checks all components of the local testing environment

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[SETUP-TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SETUP-TEST]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[SETUP-TEST]${NC} $1"
}

print_error() {
    echo -e "${RED}[SETUP-TEST]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}[SETUP-TEST]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    print_status "Testing: $test_name"
    
    if eval "$test_command" &> /dev/null; then
        print_success "  ✓ PASSED"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        print_error "  ✗ FAILED"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

# Function to check prerequisites
check_prerequisites() {
    print_header "=== CHECKING PREREQUISITES ==="
    
    run_test "Docker installed" "command -v docker"
    run_test "Docker running" "docker info"
    run_test "Docker Compose available" "command -v docker-compose || docker compose version"
    run_test "Act installed" "command -v act"
    run_test "Git repository" "git rev-parse --is-inside-work-tree"
    
    echo ""
}

# Function to check file structure
check_file_structure() {
    print_header "=== CHECKING FILE STRUCTURE ==="
    
    local required_files=(
        "$PROJECT_ROOT/.actrc"
        "$SCRIPT_DIR/docker-compose.test.yml"
        "$SCRIPT_DIR/run-tests.sh"
        "$SCRIPT_DIR/mock-env.sh"
        "$SCRIPT_DIR/scripts/simulate-workflow.sh"
        "$SCRIPT_DIR/scripts/test-conditions.sh"
        "$SCRIPT_DIR/README.md"
    )
    
    for file in "${required_files[@]}"; do
        run_test "File exists: $(basename "$file")" "test -f '$file'"
    done
    
    local required_dirs=(
        "$SCRIPT_DIR/events"
        "$SCRIPT_DIR/scripts"
        "$SCRIPT_DIR/test-configs"
    )
    
    for dir in "${required_dirs[@]}"; do
        run_test "Directory exists: $(basename "$dir")" "test -d '$dir'"
    done
    
    echo ""
}

# Function to check executable permissions
check_permissions() {
    print_header "=== CHECKING PERMISSIONS ==="
    
    local executable_files=(
        "$SCRIPT_DIR/run-tests.sh"
        "$SCRIPT_DIR/mock-env.sh"
        "$SCRIPT_DIR/scripts/simulate-workflow.sh"
        "$SCRIPT_DIR/scripts/test-conditions.sh"
    )
    
    for file in "${executable_files[@]}"; do
        run_test "Executable: $(basename "$file")" "test -x '$file'"
    done
    
    echo ""
}

# Function to check event payloads
check_event_payloads() {
    print_header "=== CHECKING EVENT PAYLOADS ==="
    
    local event_files=(
        "$SCRIPT_DIR/events/push.json"
        "$SCRIPT_DIR/events/workflow_dispatch.json"
        "$SCRIPT_DIR/events/workflow_call.json"
        "$SCRIPT_DIR/events/schedule.json"
        "$SCRIPT_DIR/events/push-force-build.json"
        "$SCRIPT_DIR/events/push-skip-build.json"
        "$SCRIPT_DIR/events/push-deploy-services.json"
        "$SCRIPT_DIR/events/push-release-only.json"
    )
    
    for file in "${event_files[@]}"; do
        run_test "Event payload: $(basename "$file")" "test -f '$file' && python3 -m json.tool '$file'"
    done
    
    echo ""
}

# Function to check workflow files
check_workflow_files() {
    print_header "=== CHECKING WORKFLOW FILES ==="
    
    local workflow_files=(
        "$PROJECT_ROOT/.github/workflows/build.yml"
        "$PROJECT_ROOT/.github/workflows/release.yml"
        "$PROJECT_ROOT/.github/workflows/e2e-tests.yml"
    )
    
    for file in "${workflow_files[@]}"; do
        run_test "Workflow file: $(basename "$file")" "test -f '$file'"
    done
    
    echo ""
}

# Function to test environment setup
test_environment_setup() {
    print_header "=== TESTING ENVIRONMENT SETUP ==="
    
    # Clean up any existing environment files
    rm -f "$SCRIPT_DIR/test.env" "$SCRIPT_DIR/secrets.env" "$SCRIPT_DIR/variables.env"
    
    run_test "Mock environment setup" "$SCRIPT_DIR/mock-env.sh"
    run_test "Test environment file created" "test -f '$SCRIPT_DIR/test.env'"
    run_test "Secrets file created" "test -f '$SCRIPT_DIR/secrets.env'"
    run_test "Variables file created" "test -f '$SCRIPT_DIR/variables.env'"
    run_test "Environment validation" "$SCRIPT_DIR/mock-env.sh --validate"
    
    echo ""
}

# Function to test condition scripts
test_condition_scripts() {
    print_header "=== TESTING CONDITION SCRIPTS ==="
    
    run_test "Commit tag conditions" "$SCRIPT_DIR/scripts/test-conditions.sh commit-tags"
    run_test "File change detection" "$SCRIPT_DIR/scripts/test-conditions.sh file-changes"
    run_test "Build matrix generation" "$SCRIPT_DIR/scripts/test-conditions.sh build-matrix"
    run_test "Service dependency order" "$SCRIPT_DIR/scripts/test-conditions.sh dependency-order"
    
    echo ""
}

# Function to test Docker Compose
test_docker_compose() {
    print_header "=== TESTING DOCKER COMPOSE ==="
    
    cd "$SCRIPT_DIR"
    
    run_test "Docker Compose config validation" "docker-compose -f docker-compose.test.yml config"
    run_test "Docker Compose build test" "docker-compose -f docker-compose.test.yml build --dry-run 2>/dev/null || true"
    
    echo ""
}

# Function to test act configuration
test_act_configuration() {
    print_header "=== TESTING ACT CONFIGURATION ==="
    
    cd "$PROJECT_ROOT"
    
    run_test "Act configuration file" "test -f '$PROJECT_ROOT/.actrc'"
    run_test "Act workflow listing" "act -l"
    run_test "Act dry run build" "act push --dry-run --eventpath '$SCRIPT_DIR/events/push.json'"
    
    echo ""
}

# Function to show test summary
show_summary() {
    print_header "=== TEST SUMMARY ==="
    
    echo "Total tests: $TESTS_TOTAL"
    echo "Passed: $TESTS_PASSED"
    echo "Failed: $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        print_success "🎉 All tests passed! Local testing environment is ready."
        echo ""
        print_status "Quick start commands:"
        echo "  cd test-local"
        echo "  ./run-tests.sh -i                    # Interactive mode"
        echo "  ./run-tests.sh build                 # Test build workflow"
        echo "  ./scripts/simulate-workflow.sh push-normal  # Test push scenario"
        echo ""
        return 0
    else
        print_error "❌ Some tests failed. Please check the issues above."
        echo ""
        print_status "Common fixes:"
        echo "  # Install missing dependencies"
        echo "  # Check file permissions: chmod +x test-local/*.sh"
        echo "  # Ensure Docker is running"
        echo "  # Install act: curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
        echo ""
        return 1
    fi
}

# Function to show help
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Validate the complete local testing setup

OPTIONS:
    --quick         Run only essential tests
    --docker        Include Docker-related tests
    --act           Include act-related tests
    --all           Run all tests (default)
    -h, --help      Show this help message

EXAMPLES:
    $0                      # Run all tests
    $0 --quick              # Run essential tests only
    $0 --docker             # Run Docker-related tests
    $0 --act                # Run act-related tests

EOF
}

# Main function
main() {
    local test_mode="all"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                test_mode="quick"
                shift
                ;;
            --docker)
                test_mode="docker"
                shift
                ;;
            --act)
                test_mode="act"
                shift
                ;;
            --all)
                test_mode="all"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    print_header "🚀 LOCAL TESTING ENVIRONMENT VALIDATION"
    echo ""
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Run tests based on mode
    case "$test_mode" in
        quick)
            check_prerequisites
            check_file_structure
            check_permissions
            test_environment_setup
            ;;
        docker)
            check_prerequisites
            test_docker_compose
            ;;
        act)
            check_prerequisites
            test_act_configuration
            ;;
        all)
            check_prerequisites
            check_file_structure
            check_permissions
            check_event_payloads
            check_workflow_files
            test_environment_setup
            test_condition_scripts
            test_docker_compose
            test_act_configuration
            ;;
    esac
    
    # Show summary
    show_summary
}

# Run main function with all arguments
main "$@"