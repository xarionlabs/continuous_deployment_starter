#!/bin/bash
set -e

export PYTHONPATH=$(pwd)/src:$PYTHONPATH

echo "Running unit tests..."
pytest test/ 