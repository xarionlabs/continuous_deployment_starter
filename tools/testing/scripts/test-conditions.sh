#!/bin/bash

# test-conditions.sh - Test specific workflow conditions and edge cases
# This script helps validate workflow logic and conditional behavior

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[TEST-CONDITIONS]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[TEST-CONDITIONS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[TEST-CONDITIONS]${NC} $1"
}

print_error() {
    echo -e "${RED}[TEST-CONDITIONS]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_LOCAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$TEST_LOCAL_DIR/.." && pwd)"

# Default values
TEST_CASE=""
VERBOSE=false
DRY_RUN=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] TEST_CASE

Test specific workflow conditions and edge cases

TEST CASES:
    commit-tags         Test all commit message tag conditions
    file-changes        Test file change detection logic
    service-detection   Test service affection detection
    environment-vars    Test environment variable handling
    error-conditions    Test error handling and edge cases
    build-matrix        Test build matrix generation
    dependency-order    Test service dependency ordering
    all                 Run all test cases

OPTIONS:
    -v, --verbose       Enable verbose output
    -d, --dry-run       Show what would be tested without running
    -h, --help          Show this help message

EXAMPLES:
    $0 commit-tags                      # Test commit message tag logic
    $0 file-changes                     # Test file change detection
    $0 -v all                           # Run all tests with verbose output
    $0 -d error-conditions              # Dry run of error condition tests

EOF
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                print_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$TEST_CASE" ]]; then
                    TEST_CASE="$1"
                else
                    print_error "Too many arguments: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

# Function to test commit message tag conditions
test_commit_tags() {
    print_status "Testing commit message tag conditions..."
    
    local test_messages=(
        "Normal commit message"
        "Force build all applications [force-build]"
        "Skip entire workflow [skip-build]"
        "Deploy specific services [deploy-services: app1,app2]"
        "Deploy all services [deploy-services: all]"
        "Release only mode [release-only]"
        "Mixed tags [force-build] and [deploy-services: app1]"
        "Case insensitive [FORCE-BUILD]"
        "With extra spaces [ force-build ]"
    )
    
    for message in "${test_messages[@]}"; do
        print_status "Testing message: $message"
        
        # Test force-build detection
        if echo "$message" | grep -qi "\[.*force-build.*\]"; then
            print_success "  Force build: DETECTED"
        else
            print_status "  Force build: not detected"
        fi
        
        # Test skip-build detection
        if echo "$message" | grep -qi "\[.*skip-build.*\]"; then
            print_success "  Skip build: DETECTED"
        else
            print_status "  Skip build: not detected"
        fi
        
        # Test deploy-services detection
        if echo "$message" | grep -qi "\[deploy-services:"; then
            local services=$(echo "$message" | grep -oiE '\[deploy-services:\s*[^\]]+\]' | sed -E 's/\[deploy-services:\s*([^\]]+)\]/\1/' | tr -d ' ')
            print_success "  Deploy services: DETECTED ($services)"
        else
            print_status "  Deploy services: not detected"
        fi
        
        # Test release-only detection
        if echo "$message" | grep -qi "\[.*release-only.*\]"; then
            print_success "  Release only: DETECTED"
        else
            print_status "  Release only: not detected"
        fi
        
        echo ""
    done
}

# Function to test file change detection
test_file_changes() {
    print_status "Testing file change detection logic..."
    
    local test_scenarios=(
        "applications/app.pxy6.com/src/app.tsx:app.pxy6.com"
        "applications/pxy6.com/package.json:pxy6.com"
        "utilities/user_management/src/manage.py:user_management"
        "release-tooling/deployment-manager/src/main.py:deployment-manager"
        "services/01_postgres/docker-compose.yml:01_postgres"
        ".github/workflows/build.yml:ALL_SERVICES"
        ".github/workflows/scripts/generate_quadlets.sh:ALL_SERVICES"
        "README.md:NO_SERVICES"
        "docs/deployment.md:NO_SERVICES"
    )
    
    for scenario in "${test_scenarios[@]}"; do
        local file_path="${scenario%:*}"
        local expected_service="${scenario#*:}"
        
        print_status "Testing file: $file_path"
        print_status "Expected service affection: $expected_service"
        
        # Simulate service detection logic
        local affected_service=""
        
        if [[ "$file_path" == applications/* ]]; then
            affected_service=$(echo "$file_path" | cut -d/ -f2)
        elif [[ "$file_path" == utilities/* ]]; then
            affected_service=$(echo "$file_path" | cut -d/ -f2)
        elif [[ "$file_path" == release-tooling/* ]]; then
            affected_service=$(echo "$file_path" | cut -d/ -f2)
        elif [[ "$file_path" == services/* ]]; then
            affected_service=$(echo "$file_path" | cut -d/ -f2)
        elif [[ "$file_path" == .github/workflows/scripts/* ]]; then
            affected_service="ALL_SERVICES"
        else
            affected_service="NO_SERVICES"
        fi
        
        if [[ "$affected_service" == "$expected_service" ]]; then
            print_success "  Service detection: CORRECT ($affected_service)"
        else
            print_error "  Service detection: INCORRECT (got: $affected_service, expected: $expected_service)"
        fi
        
        echo ""
    done
}

# Function to test service detection
test_service_detection() {
    print_status "Testing service affection detection..."
    
    # Test the actual determine_affected_services.sh script
    local script_path="$PROJECT_ROOT/.github/workflows/scripts/determine_affected_services.sh"
    
    if [[ ! -f "$script_path" ]]; then
        print_error "Script not found: $script_path"
        return 1
    fi
    
    print_status "Testing with script: $script_path"
    
    local test_cases=(
        "services/01_postgres/docker-compose.yml:01_postgres"
        "applications/app.pxy6.com/src/app.tsx applications/pxy6.com/src/app.tsx:app.pxy6.com,pxy6.com"
        ".github/workflows/scripts/generate_quadlets.sh:ALL"
        "README.md:NONE"
    )
    
    for test_case in "${test_cases[@]}"; do
        local files="${test_case%:*}"
        local expected="${test_case#*:}"
        
        print_status "Testing files: $files"
        print_status "Expected result: $expected"
        
        if [[ "$DRY_RUN" == false ]]; then
            local result=$("$script_path" "$files" "false")
            print_status "Actual result: $result"
            
            # Note: This is a simplified test - the actual script logic is more complex
            if [[ -n "$result" ]]; then
                print_success "  Service detection: Services detected"
            else
                print_status "  Service detection: No services detected"
            fi
        else
            print_status "  [DRY RUN] Would test with script"
        fi
        
        echo ""
    done
}

# Function to test environment variable handling
test_environment_vars() {
    print_status "Testing environment variable handling..."
    
    # Create temporary environment file
    local temp_env="$TEST_LOCAL_DIR/test_env_conditions.env"
    
    cat > "$temp_env" << EOF
# Test environment variables
GITHUB_REPOSITORY=owner/test-repo
GITHUB_REF=refs/heads/main
GITHUB_SHA=test_sha_123
GITHUB_EVENT_NAME=push
GITHUB_ACTOR=test_user
REGISTRY=localhost:5000
DATABASE_URL=postgresql://test:test@localhost:5432/test
EOF
    
    print_status "Created test environment file: $temp_env"
    
    # Test environment variable parsing
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        
        print_status "Testing variable: $key=$value"
        
        # Test specific variable validation
        case "$key" in
            GITHUB_REPOSITORY)
                if [[ "$value" =~ ^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$ ]]; then
                    print_success "  Repository format: VALID"
                else
                    print_error "  Repository format: INVALID"
                fi
                ;;
            GITHUB_REF)
                if [[ "$value" =~ ^refs\/(heads|tags)\/.*$ ]]; then
                    print_success "  Ref format: VALID"
                else
                    print_error "  Ref format: INVALID"
                fi
                ;;
            GITHUB_SHA)
                if [[ "$value" =~ ^[a-zA-Z0-9_]+$ ]]; then
                    print_success "  SHA format: VALID"
                else
                    print_error "  SHA format: INVALID"
                fi
                ;;
            DATABASE_URL)
                if [[ "$value" =~ ^postgresql:\/\/.*$ ]]; then
                    print_success "  Database URL format: VALID"
                else
                    print_error "  Database URL format: INVALID"
                fi
                ;;
            *)
                print_status "  Generic variable: PRESENT"
                ;;
        esac
    done < "$temp_env"
    
    # Cleanup
    rm -f "$temp_env"
    
    echo ""
}

# Function to test error conditions
test_error_conditions() {
    print_status "Testing error conditions and edge cases..."
    
    local error_scenarios=(
        "missing_dockerfile:Check handling of missing Dockerfile"
        "invalid_event:Check handling of invalid event types"
        "missing_secrets:Check handling of missing secrets"
        "network_failure:Check handling of network failures"
        "timeout_conditions:Check handling of timeouts"
    )
    
    for scenario in "${error_scenarios[@]}"; do
        local test_name="${scenario%:*}"
        local description="${scenario#*:}"
        
        print_status "Testing: $test_name"
        print_status "Description: $description"
        
        case "$test_name" in
            missing_dockerfile)
                print_status "  Simulating missing Dockerfile scenario..."
                if [[ "$DRY_RUN" == false ]]; then
                    # Test would involve temporarily moving/renaming Dockerfile
                    print_warning "  [SIMULATION] Would test missing Dockerfile handling"
                else
                    print_status "  [DRY RUN] Would simulate missing Dockerfile"
                fi
                ;;
            invalid_event)
                print_status "  Testing invalid event handling..."
                # Test with malformed event JSON
                print_warning "  [SIMULATION] Would test invalid event JSON handling"
                ;;
            missing_secrets)
                print_status "  Testing missing secrets handling..."
                # Test with missing secrets file
                print_warning "  [SIMULATION] Would test missing secrets file handling"
                ;;
            network_failure)
                print_status "  Testing network failure simulation..."
                # Test with network connectivity issues
                print_warning "  [SIMULATION] Would test network failure handling"
                ;;
            timeout_conditions)
                print_status "  Testing timeout conditions..."
                # Test with long-running operations
                print_warning "  [SIMULATION] Would test timeout handling"
                ;;
        esac
        
        echo ""
    done
}

# Function to test build matrix generation
test_build_matrix() {
    print_status "Testing build matrix generation..."
    
    # Test application discovery
    print_status "Discovering applications with Dockerfiles..."
    
    local applications=()
    while IFS= read -r -d '' dir; do
        local app_name=$(basename "$dir")
        if [[ -f "$dir/Dockerfile" ]]; then
            applications+=("$app_name")
            print_success "  Found application: $app_name"
        fi
    done < <(find "$PROJECT_ROOT/applications" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
    
    # Test utility discovery
    print_status "Discovering utilities with Dockerfiles..."
    
    local utilities=()
    while IFS= read -r -d '' dir; do
        local util_name=$(basename "$dir")
        if [[ -f "$dir/Dockerfile" ]]; then
            utilities+=("$util_name")
            print_success "  Found utility: $util_name"
        fi
    done < <(find "$PROJECT_ROOT/utilities" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
    
    # Test release tooling discovery
    print_status "Discovering release tools with Dockerfiles..."
    
    local release_tools=()
    while IFS= read -r -d '' dir; do
        local tool_name=$(basename "$dir")
        if [[ -f "$dir/Dockerfile" ]]; then
            release_tools+=("$tool_name")
            print_success "  Found release tool: $tool_name"
        fi
    done < <(find "$PROJECT_ROOT/release-tooling" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
    
    # Generate build matrix
    local all_buildable=()
    all_buildable+=("${applications[@]}")
    all_buildable+=("${utilities[@]}")
    all_buildable+=("${release_tools[@]}")
    
    print_status "Generated build matrix:"
    for item in "${all_buildable[@]}"; do
        print_status "  - $item"
    done
    
    echo ""
}

# Function to test dependency ordering
test_dependency_order() {
    print_status "Testing service dependency ordering..."
    
    # Test service discovery
    print_status "Discovering services..."
    
    local services=()
    while IFS= read -r -d '' dir; do
        local service_name=$(basename "$dir")
        services+=("$service_name")
        print_status "  Found service: $service_name"
    done < <(find "$PROJECT_ROOT/services" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null)
    
    # Test dependency order (based on service naming convention)
    print_status "Testing dependency order logic..."
    
    IFS=$'\n' sorted_services=($(sort <<<"${services[*]}"))
    
    print_status "Services in dependency order:"
    for service in "${sorted_services[@]}"; do
        print_status "  $service"
    done
    
    echo ""
}

# Function to run all test cases
run_all_tests() {
    print_status "Running all test cases..."
    
    local test_functions=(
        "test_commit_tags"
        "test_file_changes"
        "test_service_detection"
        "test_environment_vars"
        "test_error_conditions"
        "test_build_matrix"
        "test_dependency_order"
    )
    
    for test_func in "${test_functions[@]}"; do
        print_status "========================================="
        $test_func
        print_status "========================================="
        echo ""
    done
    
    print_success "All test cases completed"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Validate inputs
    if [[ -z "$TEST_CASE" ]]; then
        print_error "No test case specified"
        show_usage
        exit 1
    fi
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    print_status "Running test case: $TEST_CASE"
    echo ""
    
    # Run specified test case
    case "$TEST_CASE" in
        commit-tags)
            test_commit_tags
            ;;
        file-changes)
            test_file_changes
            ;;
        service-detection)
            test_service_detection
            ;;
        environment-vars)
            test_environment_vars
            ;;
        error-conditions)
            test_error_conditions
            ;;
        build-matrix)
            test_build_matrix
            ;;
        dependency-order)
            test_dependency_order
            ;;
        all)
            run_all_tests
            ;;
        *)
            print_error "Unknown test case: $TEST_CASE"
            show_usage
            exit 1
            ;;
    esac
    
    print_success "Test case completed: $TEST_CASE"
}

# Run main function with all arguments
main "$@"