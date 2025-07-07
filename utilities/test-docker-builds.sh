#!/bin/bash

# Script to test Docker builds for all applications and utilities
# Run this after modifying any Dockerfiles

set -e

echo "🐳 Testing Docker builds for all applications and utilities..."

# Function to test build in a directory
test_build() {
    local dir=$1
    local name=$(basename "$dir")
    
    if [ -f "$dir/Dockerfile" ]; then
        echo "📦 Building $name..."
        cd "$dir"
        if docker build -t "test-$name:latest" . > /dev/null 2>&1; then
            echo "✅ $name build successful"
        else
            echo "❌ $name build failed"
            return 1
        fi
        cd - > /dev/null
    fi
}

# Test all applications
echo "Testing applications..."
for app_dir in applications/*/; do
    test_build "$app_dir"
done

# Test all utilities
echo "Testing utilities..."
for util_dir in utilities/*/; do
    test_build "$util_dir"
done

# Test release tooling
if [ -f "release-tooling/pytool/Dockerfile" ]; then
    test_build "release-tooling/pytool"
fi

# Test services
echo "Testing services..."
for service_dir in services/*/; do
    test_build "$service_dir"
done

echo "🎉 All Docker builds tested!"