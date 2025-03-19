#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! nc -z ${POSTGRES_HOST} 5432; do
  sleep 0.1
done
echo "Database is ready!"

export PYTHONPATH=$(pwd)/src:$PYTHONPATH
fastapi dev src/api/main.py --host 0.0.0.0 --port 8000
