#!/bin/bash

# simulate-workflow.sh - Simulate GitHub Actions workflow events and conditions
# This script helps test various workflow scenarios locally

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[SIMULATE]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SIMULATE]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[SIMULATE]${NC} $1"
}

print_error() {
    echo -e "${RED}[SIMULATE]${NC} $1"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_LOCAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$TEST_LOCAL_DIR/.." && pwd)"

# Default values
SCENARIO=""
WORKFLOW=""
ENVIRONMENT="test"
VERBOSE=false
DRY_RUN=false

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS] SCENARIO [WORKFLOW]

Simulate GitHub Actions workflow events and conditions

SCENARIOS:
    push-normal         Normal push event with file changes
    push-force-build    Push with [force-build] commit message
    push-skip-build     Push with [skip-build] commit message
    push-deploy-services Push with [deploy-services: ...] commit message
    push-release-only   Push with [release-only] commit message
    manual-dispatch     Manual workflow dispatch
    scheduled-run       Scheduled workflow run
    release-staging     Release to staging environment
    release-live        Release to live environment
    e2e-test            End-to-end test execution

WORKFLOWS:
    build               Build workflow
    release             Release workflow
    e2e-tests           E2E tests workflow
    all                 All workflows (default)

OPTIONS:
    -e, --environment   Environment to simulate (test, staging, live)
    -v, --verbose       Enable verbose output
    -d, --dry-run       Show what would be executed without running
    -h, --help          Show this help message

EXAMPLES:
    $0 push-normal build                    # Test normal push triggering build
    $0 push-force-build                     # Test force build scenario
    $0 -e staging release-staging           # Test staging release
    $0 -v -d manual-dispatch                # Dry run of manual dispatch
    $0 scheduled-run release                # Test scheduled release

EOF
}

# Function to parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
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
                if [[ -z "$SCENARIO" ]]; then
                    SCENARIO="$1"
                elif [[ -z "$WORKFLOW" ]]; then
                    WORKFLOW="$1"
                else
                    print_error "Too many arguments: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Set default workflow if not specified
    if [[ -z "$WORKFLOW" ]]; then
        WORKFLOW="all"
    fi
}

# Function to validate scenario
validate_scenario() {
    local valid_scenarios=(
        "push-normal"
        "push-force-build"
        "push-skip-build"
        "push-deploy-services"
        "push-release-only"
        "manual-dispatch"
        "scheduled-run"
        "release-staging"
        "release-live"
        "e2e-test"
    )
    
    if [[ ! " ${valid_scenarios[*]} " =~ " ${SCENARIO} " ]]; then
        print_error "Invalid scenario: $SCENARIO"
        print_error "Valid scenarios: ${valid_scenarios[*]}"
        exit 1
    fi
}

# Function to validate workflow
validate_workflow() {
    local valid_workflows=(
        "build"
        "release"
        "e2e-tests"
        "all"
    )
    
    if [[ ! " ${valid_workflows[*]} " =~ " ${WORKFLOW} " ]]; then
        print_error "Invalid workflow: $WORKFLOW"
        print_error "Valid workflows: ${valid_workflows[*]}"
        exit 1
    fi
}

# Function to setup test environment
setup_test_environment() {
    print_status "Setting up test environment for scenario: $SCENARIO"
    
    # Setup mock environment
    source "$TEST_LOCAL_DIR/mock-env.sh"
    
    # Create scenario-specific environment modifications
    case $SCENARIO in
        push-force-build)
            echo "FORCE_BUILD=true" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        push-skip-build)
            echo "SKIP_BUILD=true" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        push-deploy-services)
            echo "DEPLOY_SERVICES=04_app_pxy6_com,05_pxy6_web" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        push-release-only)
            echo "RELEASE_ONLY=true" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        manual-dispatch)
            echo "GITHUB_EVENT_NAME=workflow_dispatch" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        scheduled-run)
            echo "GITHUB_EVENT_NAME=schedule" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        release-staging)
            echo "ENVIRONMENT=staging" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        release-live)
            echo "ENVIRONMENT=live" >> "$TEST_LOCAL_DIR/test.env"
            ;;
        e2e-test)
            echo "ENVIRONMENT=$ENVIRONMENT" >> "$TEST_LOCAL_DIR/test.env"
            ;;
    esac
    
    print_success "Test environment setup completed"
}

# Function to get event file for scenario
get_event_file() {
    case $SCENARIO in
        push-normal)
            echo "$TEST_LOCAL_DIR/events/push.json"
            ;;
        push-force-build)
            echo "$TEST_LOCAL_DIR/events/push-force-build.json"
            ;;
        push-skip-build)
            echo "$TEST_LOCAL_DIR/events/push-skip-build.json"
            ;;
        push-deploy-services)
            echo "$TEST_LOCAL_DIR/events/push-deploy-services.json"
            ;;
        push-release-only)
            echo "$TEST_LOCAL_DIR/events/push-release-only.json"
            ;;
        manual-dispatch)
            echo "$TEST_LOCAL_DIR/events/workflow_dispatch.json"
            ;;
        scheduled-run)
            echo "$TEST_LOCAL_DIR/events/schedule.json"
            ;;
        release-staging|release-live)
            echo "$TEST_LOCAL_DIR/events/workflow_call.json"
            ;;
        e2e-test)
            echo "$TEST_LOCAL_DIR/events/workflow_call.json"
            ;;
        *)
            echo "$TEST_LOCAL_DIR/events/push.json"
            ;;
    esac
}

# Function to get event type for scenario
get_event_type() {
    case $SCENARIO in
        push-*)
            echo "push"
            ;;
        manual-dispatch)
            echo "workflow_dispatch"
            ;;
        scheduled-run)
            echo "schedule"
            ;;
        release-*|e2e-test)
            echo "workflow_call"
            ;;
        *)
            echo "push"
            ;;
    esac
}

# Function to simulate workflow execution
simulate_workflow() {
    local workflow_name=$1
    local event_file=$(get_event_file)
    local event_type=$(get_event_type)
    
    print_status "Simulating workflow: $workflow_name"
    print_status "Event type: $event_type"
    print_status "Event file: $event_file"
    
    if [[ ! -f "$event_file" ]]; then
        print_error "Event file not found: $event_file"
        return 1
    fi
    
    # Construct act command
    local act_cmd="act $event_type"
    act_cmd+=" --eventpath $event_file"
    act_cmd+=" --workflows $PROJECT_ROOT/.github/workflows/${workflow_name}.yml"
    act_cmd+=" --env-file $TEST_LOCAL_DIR/test.env"
    
    if [[ -f "$TEST_LOCAL_DIR/secrets.env" ]]; then
        act_cmd+=" --secret-file $TEST_LOCAL_DIR/secrets.env"
    fi
    
    if [[ -f "$TEST_LOCAL_DIR/variables.env" ]]; then
        act_cmd+=" --var-file $TEST_LOCAL_DIR/variables.env"
    fi
    
    if [[ "$VERBOSE" == true ]]; then
        act_cmd+=" --verbose"
    fi
    
    # Execute or show dry run
    if [[ "$DRY_RUN" == true ]]; then
        print_status "DRY RUN - Would execute:"
        echo "  $act_cmd"
    else
        print_status "Executing: $act_cmd"
        cd "$PROJECT_ROOT"
        eval $act_cmd
        local exit_code=$?
        
        if [[ $exit_code -eq 0 ]]; then
            print_success "Workflow $workflow_name simulation completed successfully"
        else
            print_error "Workflow $workflow_name simulation failed with exit code: $exit_code"
            return $exit_code
        fi
    fi
}

# Function to simulate all workflows
simulate_all_workflows() {
    print_status "Simulating all workflows for scenario: $SCENARIO"
    
    local workflows=("build" "release" "e2e-tests")
    local failed_workflows=()
    
    for workflow in "${workflows[@]}"; do
        if ! simulate_workflow "$workflow"; then
            failed_workflows+=("$workflow")
        fi
    done
    
    if [[ ${#failed_workflows[@]} -eq 0 ]]; then
        print_success "All workflows completed successfully"
    else
        print_error "The following workflows failed: ${failed_workflows[*]}"
        return 1
    fi
}

# Function to show scenario summary
show_scenario_summary() {
    print_status "Scenario Summary:"
    echo "  - Scenario: $SCENARIO"
    echo "  - Workflow: $WORKFLOW"
    echo "  - Environment: $ENVIRONMENT"
    echo "  - Event Type: $(get_event_type)"
    echo "  - Event File: $(get_event_file)"
    echo "  - Verbose: $VERBOSE"
    echo "  - Dry Run: $DRY_RUN"
    echo ""
    
    case $SCENARIO in
        push-normal)
            echo "This scenario simulates a normal push event with file changes."
            echo "It will trigger the build workflow and potentially release workflows."
            ;;
        push-force-build)
            echo "This scenario simulates a push with [force-build] commit message."
            echo "It will force building all applications regardless of changes."
            ;;
        push-skip-build)
            echo "This scenario simulates a push with [skip-build] commit message."
            echo "It will skip the entire build and release process."
            ;;
        push-deploy-services)
            echo "This scenario simulates a push with [deploy-services: ...] commit message."
            echo "It will deploy only the specified services."
            ;;
        push-release-only)
            echo "This scenario simulates a push with [release-only] commit message."
            echo "It will skip builds but proceed with releases using latest images."
            ;;
        manual-dispatch)
            echo "This scenario simulates a manual workflow dispatch."
            echo "It allows testing workflows with custom inputs."
            ;;
        scheduled-run)
            echo "This scenario simulates a scheduled workflow run."
            echo "It tests workflows triggered by cron schedules."
            ;;
        release-staging)
            echo "This scenario simulates a release to staging environment."
            echo "It tests the staging deployment pipeline."
            ;;
        release-live)
            echo "This scenario simulates a release to live environment."
            echo "It tests the production deployment pipeline."
            ;;
        e2e-test)
            echo "This scenario simulates end-to-end test execution."
            echo "It tests the e2e testing pipeline."
            ;;
    esac
}

# Function to cleanup simulation
cleanup_simulation() {
    print_status "Cleaning up simulation environment..."
    
    # Remove temporary environment modifications
    if [[ -f "$TEST_LOCAL_DIR/test.env" ]]; then
        # Remove scenario-specific lines
        sed -i.bak '/^FORCE_BUILD=/d; /^SKIP_BUILD=/d; /^DEPLOY_SERVICES=/d; /^RELEASE_ONLY=/d; /^GITHUB_EVENT_NAME=/d; /^ENVIRONMENT=/d' "$TEST_LOCAL_DIR/test.env"
        rm -f "$TEST_LOCAL_DIR/test.env.bak"
    fi
    
    print_success "Simulation cleanup completed"
}

# Main function
main() {
    # Parse arguments
    parse_args "$@"
    
    # Validate inputs
    if [[ -z "$SCENARIO" ]]; then
        print_error "No scenario specified"
        show_usage
        exit 1
    fi
    
    validate_scenario
    validate_workflow
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Show scenario summary
    show_scenario_summary
    
    # Setup test environment
    setup_test_environment
    
    # Simulate workflow(s)
    if [[ "$WORKFLOW" == "all" ]]; then
        simulate_all_workflows
    else
        simulate_workflow "$WORKFLOW"
    fi
    
    # Cleanup
    cleanup_simulation
    
    print_success "Simulation completed"
}

# Run main function with all arguments
main "$@"