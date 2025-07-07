#!/bin/bash
set -e

echo "Running e2e tests for deployment-manager..."

# Basic e2e test - just check that the tool runs and shows help
release-tool --help

echo "E2E tests passed!"