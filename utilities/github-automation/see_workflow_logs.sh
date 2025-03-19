#!/bin/bash

# Exit on error
set -e
# change directory to the script's directory
cd "$(dirname "$0")"

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
RUN_INFO=$(gh run list --limit 1 --json databaseId,workflowName,status,startedAt | cat)

if [ -z "$RUN_INFO" ]; then
    echo "No workflow runs found."
    exit 1
fi

# Get the run ID using Python
RUN_ID=$(echo "$RUN_INFO" | python3 -c "import sys, json; print(json.load(sys.stdin)[0]['databaseId'])")

# Get jobs information
echo "Fetching job details..."
JOBS_INFO=$(gh run view "$RUN_ID" --json jobs | cat)

# Process the JSON data
echo "Processing workflow logs..."
echo "$RUN_INFO" | python3 parse_workflow_logs.py --run-info
echo "$JOBS_INFO" | python3 parse_workflow_logs.py --jobs-info

# Get the failed logs if any
echo "Fetching failed job logs..."
gh run view "$RUN_ID" --log-failed | cat 


cd -