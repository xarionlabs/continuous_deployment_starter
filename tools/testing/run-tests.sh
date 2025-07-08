#!/bin/bash

# run-tests.sh - Local CI/CD Pipeline Testing Script
# This script provides a comprehensive local testing environment for the CI/CD pipeline

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_LOCAL_DIR="$PROJECT_ROOT/test-local"
COMPOSE_FILE="$TEST_LOCAL_DIR/docker-compose.test.yml"
LOGS_DIR="$TEST_LOCAL_DIR/logs"
ARTIFACTS_DIR="$TEST_LOCAL_DIR/artifacts"

# Default values
WORKFLOW=""
EVENT_TYPE="push"
ENVIRONMENT="test"
CLEANUP=false
VERBOSE=false
INTERACTIVE=false
SKIP_SETUP=false
PROFILE="default"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] [WORKFLOW]

Local CI/CD Pipeline Testing Script

ARGUMENTS:
    WORKFLOW            Workflow to test (build, release, e2e-tests, or all)

OPTIONS:
    -e, --event         Event type to simulate (push, workflow_dispatch, schedule)
    -E, --environment   Environment to test (test, staging, live)
    -p, --profile       Docker Compose profile to use (default, integration-test, mock-services)
    -c, --cleanup       Clean up test environment after running
    -v, --verbose       Enable verbose output
    -i, --interactive   Run in interactive mode
    -s, --skip-setup    Skip infrastructure setup
    -h, --help          Show this help message

EXAMPLES:
    $0 build                           # Test build workflow with push event
    $0 -e workflow_dispatch build      # Test build workflow with manual trigger
    $0 -E staging release              # Test release workflow for staging
    $0 -p integration-test all         # Test all workflows with integration tests
    $0 -c -v build                     # Test build workflow with cleanup and verbose output
    $0 -i                              # Run in interactive mode

PROFILES:
    default             Basic testing infrastructure (postgres, redis, registry)
    integration-test    Includes test applications for integration testing
    mock-services       Includes mock external services (WireMock)

WORKFLOWS:
    build               Test the build workflow (.github/workflows/build.yml)
    release             Test the release workflow (.github/workflows/release.yml)
    e2e-tests           Test the e2e-tests workflow (.github/workflows/e2e-tests.yml)
    all                 Test all workflows in sequence

EOF
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--event)
                EVENT_TYPE="$2"
                shift 2
                ;;
            -E|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -p|--profile)
                PROFILE="$2"
                shift 2
                ;;
            -c|--cleanup)
                CLEANUP=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -i|--interactive)
                INTERACTIVE=true
                shift
                ;;
            -s|--skip-setup)
                SKIP_SETUP=true
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
                if [[ -z "$WORKFLOW" ]]; then
                    WORKFLOW="$1"
                else
                    print_error "Multiple workflows specified: $WORKFLOW and $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if act is installed
    if ! command -v act &> /dev/null; then
        print_error "act is not installed. Please install it first:"
        print_error "  https://github.com/nektos/act#installation"
        exit 1
    fi
    
    # Check if docker is installed and running
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        print_error "Docker Compose is not available. Please install it first."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Function to setup test environment
setup_environment() {
    if [[ "$SKIP_SETUP" == true ]]; then
        print_status "Skipping environment setup"
        return
    fi
    
    print_status "Setting up test environment..."
    
    # Create necessary directories
    mkdir -p "$LOGS_DIR" "$ARTIFACTS_DIR"
    
    # Setup mock environment variables
    source "$TEST_LOCAL_DIR/mock-env.sh"
    
    # Start infrastructure services
    print_status "Starting infrastructure services..."
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" --profile "$PROFILE" up -d
    else
        docker compose -f "$COMPOSE_FILE" --profile "$PROFILE" up -d
    fi
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Check service health
    check_service_health
    
    print_success "Test environment setup completed"
}

# Function to check service health
check_service_health() {
    print_status "Checking service health..."
    
    # Check PostgreSQL
    if ! docker exec postgres-test pg_isready -U test_user -d test_db &> /dev/null; then
        print_warning "PostgreSQL test database is not ready"
    else
        print_success "PostgreSQL test database is ready"
    fi
    
    # Check Redis
    if ! docker exec redis-test redis-cli ping &> /dev/null; then
        print_warning "Redis test instance is not ready"
    else
        print_success "Redis test instance is ready"
    fi
    
    # Check Registry
    if ! curl -s http://localhost:5000/v2/ &> /dev/null; then
        print_warning "Local container registry is not ready"
    else
        print_success "Local container registry is ready"
    fi
}

# Function to run workflow with act
run_workflow() {
    local workflow_name=$1
    local event_file="$TEST_LOCAL_DIR/events/${EVENT_TYPE}.json"
    
    print_status "Running workflow: $workflow_name with event: $EVENT_TYPE"
    
    # Check if event file exists
    if [[ ! -f "$event_file" ]]; then
        print_error "Event file not found: $event_file"
        print_error "Available events: $(ls -1 "$TEST_LOCAL_DIR/events/" | grep -E '\.json$' | sed 's/\.json$//' | tr '\n' ' ')"
        exit 1
    fi
    
    # Construct act command
    local act_cmd="act"
    
    # Add event type and payload
    act_cmd+=" $EVENT_TYPE"
    act_cmd+=" --eventpath $event_file"
    
    # Add workflow file
    act_cmd+=" --workflows .github/workflows/${workflow_name}.yml"
    
    # Add verbose flag if requested
    if [[ "$VERBOSE" == true ]]; then
        act_cmd+=" --verbose"
    fi
    
    # Add environment variables
    act_cmd+=" --env-file $TEST_LOCAL_DIR/test.env"
    
    # Add secrets if available
    if [[ -f "$TEST_LOCAL_DIR/secrets.env" ]]; then
        act_cmd+=" --secret-file $TEST_LOCAL_DIR/secrets.env"
    fi
    
    # Add variables if available
    if [[ -f "$TEST_LOCAL_DIR/variables.env" ]]; then
        act_cmd+=" --var-file $TEST_LOCAL_DIR/variables.env"
    fi
    
    # Run the command
    print_status "Executing: $act_cmd"
    
    if [[ "$VERBOSE" == true ]]; then
        eval $act_cmd
    else
        eval $act_cmd > "$LOGS_DIR/${workflow_name}-${EVENT_TYPE}.log" 2>&1
    fi
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        print_success "Workflow $workflow_name completed successfully"
    else
        print_error "Workflow $workflow_name failed with exit code: $exit_code"
        if [[ "$VERBOSE" == false ]]; then
            print_error "Check logs at: $LOGS_DIR/${workflow_name}-${EVENT_TYPE}.log"
        fi
        return $exit_code
    fi
}

# Function to run interactive mode
run_interactive() {
    print_status "Running in interactive mode..."
    
    while true; do
        echo ""
        echo "Select an option:"
        echo "1. Test build workflow"
        echo "2. Test release workflow"
        echo "3. Test e2e-tests workflow"
        echo "4. Test all workflows"
        echo "5. Check service health"
        echo "6. View logs"
        echo "7. Clean up environment"
        echo "8. Exit"
        echo -n "Enter your choice (1-8): "
        
        read -r choice
        
        case $choice in
            1)
                run_workflow "build"
                ;;
            2)
                run_workflow "release"
                ;;
            3)
                run_workflow "e2e-tests"
                ;;
            4)
                run_workflow "build" && run_workflow "release" && run_workflow "e2e-tests"
                ;;
            5)
                check_service_health
                ;;
            6)
                echo "Available logs:"
                ls -la "$LOGS_DIR"
                echo -n "Enter log filename to view (or press Enter to skip): "
                read -r log_file
                if [[ -n "$log_file" && -f "$LOGS_DIR/$log_file" ]]; then
                    less "$LOGS_DIR/$log_file"
                fi
                ;;
            7)
                cleanup_environment
                ;;
            8)
                break
                ;;
            *)
                print_error "Invalid choice. Please select 1-8."
                ;;
        esac
    done
}

# Function to cleanup test environment
cleanup_environment() {
    print_status "Cleaning up test environment..."
    
    # Stop and remove containers
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" --profile "$PROFILE" down -v
    else
        docker compose -f "$COMPOSE_FILE" --profile "$PROFILE" down -v
    fi
    
    # Remove temporary files
    rm -rf "$LOGS_DIR"/* "$ARTIFACTS_DIR"/*
    
    # Clean up Docker resources
    docker system prune -f
    
    print_success "Test environment cleaned up"
}

# Function to run all workflows
run_all_workflows() {
    print_status "Running all workflows..."
    
    local failed_workflows=()
    
    # Test build workflow
    if ! run_workflow "build"; then
        failed_workflows+=("build")
    fi
    
    # Test release workflow
    if ! run_workflow "release"; then
        failed_workflows+=("release")
    fi
    
    # Test e2e-tests workflow
    if ! run_workflow "e2e-tests"; then
        failed_workflows+=("e2e-tests")
    fi
    
    # Report results
    if [[ ${#failed_workflows[@]} -eq 0 ]]; then
        print_success "All workflows completed successfully"
    else
        print_error "The following workflows failed: ${failed_workflows[*]}"
        return 1
    fi
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Check prerequisites
    check_prerequisites
    
    # Setup test environment
    setup_environment
    
    # Run tests
    if [[ "$INTERACTIVE" == true ]]; then
        run_interactive
    elif [[ "$WORKFLOW" == "all" ]]; then
        run_all_workflows
    elif [[ -n "$WORKFLOW" ]]; then
        run_workflow "$WORKFLOW"
    else
        print_error "No workflow specified. Use -h for help."
        exit 1
    fi
    
    # Cleanup if requested
    if [[ "$CLEANUP" == true ]]; then
        cleanup_environment
    fi
    
    print_success "Local testing completed"
}

# Run main function with all arguments
main "$@"