#!/bin/bash

set -e

echo "Waiting for API to be ready..."
wget --waitretry=2 --retry-connrefused --tries=10 -O /dev/null http://${APP_1_API_VIRTUAL_HOST}:8000/health || (echo 'API failed to start' && exit 1)

echo "Running e2e tests..."
pytest e2e_tests/ -v --api-url=http://${APP_1_API_VIRTUAL_HOST}:8000 --api-key=${STAGING_API_KEY}