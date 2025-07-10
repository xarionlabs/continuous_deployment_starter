#!/bin/bash

# Exit on error
set -e

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker first."
    exit 1
fi

# Function to run a workflow
run_workflow() {
    local workflow=$1
    local event=$2
    local inputs=$3
    
    echo "----------------------------------------"
    echo "Testing workflow: $workflow"
    echo "Event: $event"
    echo "Inputs: $inputs"
    echo "----------------------------------------"
    
    # Run the workflow
    if docker run --rm \
        -v "$(pwd)/../../:/github/workspace" \
        -v "$(pwd)/../../.github/workflows:/github/workflow" \
        -v "$(pwd)/../../.github/workflows/scripts:/github/scripts" \
        -e GITHUB_WORKFLOW="$workflow" \
        -e GITHUB_EVENT_NAME="$event" \
        -e GITHUB_EVENT_PATH=/github/workflow/event.json \
        -e GITHUB_WORKSPACE=/github/workspace \
        -e GITHUB_REF=refs/heads/main \
        -e GITHUB_SHA=$(git rev-parse HEAD) \
        -e GITHUB_REPOSITORY=xarionlabs/continuous_deployment_starter \
        -e GITHUB_ACTOR=test-user \
        -e GITHUB_TOKEN=test-token \
        -e INPUTS="$inputs" \
        -e REGISTRY=ghcr.io \
        -e HOST=test-host \
        -e USERNAME=test-user \
        -e KEY=test-key \
        -e ACT_LOG_LEVEL=debug \
        catthehacker/ubuntu:act-latest; then
        echo "✅ Workflow $workflow completed successfully"
    else
        echo "❌ Workflow $workflow failed"
        exit 1
    fi
    echo "----------------------------------------"
}

# Create event.json for workflow_dispatch
cat > ../../.github/workflows/event.json << EOF
{
    "inputs": {
        "build_tag": "20240319-test",
        "force_build_all": true
    }
}
EOF

# Test build workflow
run_workflow "build" "workflow_dispatch" '{"build_tag":"20240319-test","force_build_all":true}'

# Test release workflow
run_workflow "release" "workflow_call" '{"environment":"staging"}'

# Clean up
rm ../../.github/workflows/event.json

echo "All workflow tests completed" 