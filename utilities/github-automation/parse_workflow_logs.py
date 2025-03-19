#!/usr/bin/env python3

import json
import sys
from typing import Dict, Any

# ANSI color codes
GREEN = '\033[32m'
RED = '\033[31m'
YELLOW = '\033[33m'
WHITE = '\033[37m'
RESET = '\033[0m'

def get_conclusion_color(conclusion: str) -> str:
    """Get the appropriate color for a job/step conclusion."""
    colors = {
        "success": GREEN,
        "failure": RED,
        "skipped": YELLOW,
        "cancelled": RED,
        "neutral": WHITE,
        "timed_out": RED,
        "action_required": YELLOW
    }
    return colors.get(conclusion, WHITE)

def format_run_info(run_data: Dict[str, Any]) -> str:
    """Format the workflow run information."""
    run = run_data[0]
    return (
        f"Latest workflow run:\n"
        f"ID: {run['databaseId']}\n"
        f"Workflow: {run['workflowName']}\n"
        f"Status: {run['status']}\n"
        f"Started at: {run['startedAt']}\n"
        f"{'-' * 40}"
    )

def format_job_info(job: Dict[str, Any]) -> str:
    """Format a single job's information with its steps."""
    color = get_conclusion_color(job.get('conclusion', ''))
    output = [f"{color}Job: {job['name']} (Conclusion: {job.get('conclusion', 'unknown')}){RESET}"]
    
    if 'steps' in job:
        for step in job['steps']:
            step_color = get_conclusion_color(step.get('conclusion', ''))
            output.append(
                f"  {step_color}Step: {step['name']} "
                f"(Conclusion: {step.get('conclusion', 'unknown')}){RESET}"
            )
    
    output.append('-' * 40)
    return '\n'.join(output)

def process_run_info():
    """Process and display run information from stdin."""
    try:
        run_data = json.load(sys.stdin)
        print(format_run_info(run_data))
    except json.JSONDecodeError:
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)

def process_jobs_info():
    """Process and display jobs information from stdin."""
    try:
        jobs_data = json.load(sys.stdin)
        print("Job details:")
        for job in jobs_data['jobs']:
            print(format_job_info(job))
            print()
    except json.JSONDecodeError:
        print("Error: Invalid JSON input", file=sys.stderr)
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: get_workflow_logs.py [--run-info|--jobs-info]", file=sys.stderr)
        sys.exit(1)

    arg = sys.argv[1]
    if arg == "--run-info":
        process_run_info()
    elif arg == "--jobs-info":
        process_jobs_info()
    else:
        print("Error: Invalid argument", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 