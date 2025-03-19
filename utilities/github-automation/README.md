# GitHub Automation Tools

This directory contains utility scripts for automating GitHub-related tasks.

## Scripts

### get_latest_workflow_logs.sh

This script fetches and displays the logs of the latest GitHub Actions workflow run. It will:
1. Get the latest workflow run details
2. Wait for the workflow to complete
3. Display any failed job logs

Requirements:
- GitHub CLI (`gh`) installed and authenticated

Usage:
```bash
./see_workflow_logs.sh
```

