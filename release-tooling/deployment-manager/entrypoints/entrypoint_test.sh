#!/bin/bash
set -e

echo "Running tests for deployment-manager..."

# Since pytest is not available in the runtime image (dev dependencies excluded),
# we'll do basic smoke tests to verify the tool works
cd /app

# Test that the tool can be imported and run
echo "Testing tool import and basic functionality..."
python -c "from src.release_tool.main import app; print('✓ Tool imports successfully')"

# Test that the CLI commands are available
echo "Testing CLI commands..."
release-tool --help > /dev/null && echo "✓ CLI help works"
release-tool determine-changes --help > /dev/null && echo "✓ determine-changes command available"
release-tool generate-units --help > /dev/null && echo "✓ generate-units command available"
release-tool manage-services --help > /dev/null && echo "✓ manage-services command available"
release-tool pull-images --help > /dev/null && echo "✓ pull-images command available"

echo "All smoke tests passed!"