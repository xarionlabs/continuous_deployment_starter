#!/bin/bash

# Exit on error
set -e

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed. Please install it first."
    echo "Visit: https://cli.github.com/manual/installation"
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "Please authenticate with GitHub first using: gh auth login"
    exit 1
fi

# Get the latest workflow run
echo "Fetching the latest workflow run..."
LATEST_RUN=$(gh run list --limit 1 --json databaseId,workflowName,status,startedAt | cat)

if [ -z "$LATEST_RUN" ]; then
    echo "No workflow runs found."
    exit 1
fi

# Extract run details using our jq wrapper
RUN_ID=$(echo "$LATEST_RUN" | ./run_with_jq.sh -r '.[0].databaseId')
WORKFLOW_NAME=$(echo "$LATEST_RUN" | ./run_with_jq.sh -r '.[0].workflowName')
STATUS=$(echo "$LATEST_RUN" | ./run_with_jq.sh -r '.[0].status')
STARTED_AT=$(echo "$LATEST_RUN" | ./run_with_jq.sh -r '.[0].startedAt')

echo "Latest workflow run:"
echo "ID: $RUN_ID"
echo "Workflow: $WORKFLOW_NAME"
echo "Status: $STATUS"
echo "Started at: $STARTED_AT"
echo "----------------------------------------"

# Function to get current status
get_status() {
    gh run view "$RUN_ID" --json status | ./run_with_jq.sh -r '.status'
}

# Wait for the run to complete
echo "Waiting for workflow to complete..."
while true; do
    CURRENT_STATUS=$(get_status)
    
    case $CURRENT_STATUS in
        "completed")
            echo "Workflow completed!"
            break
            ;;
        "failure")
            echo "Workflow failed!"
            break
            ;;
        "success")
            echo "Workflow succeeded!"
            break
            ;;
        "cancelled")
            echo "Workflow was cancelled!"
            break
            ;;
        *)
            echo -ne "Status: $CURRENT_STATUS...\r"
            sleep 5
            ;;
    esac
done

echo "----------------------------------------"

# Get the failed logs if any
echo "Fetching failed job logs..."
gh run view "$RUN_ID" --log-failed | cat 