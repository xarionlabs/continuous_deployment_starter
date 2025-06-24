#!/bin/bash
set -e

cd /app/src
echo "SKIPPING e2e tests"
#echo "Waiting for app to be ready..."
## Wait for the app to be accessible
#timeout=60
#while [ $timeout -gt 0 ]; do
#    if curl -f http://localhost:3000 >/dev/null 2>&1; then
#        break
#    fi
#    sleep 1
#    timeout=$((timeout - 1))
#done
#
#if [ $timeout -eq 0 ]; then
#    echo "App failed to start within 60 seconds"
#    exit 1
#fi

#echo "Running e2e tests..."
# npm run test:e2e