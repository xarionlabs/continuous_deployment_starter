#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! nc -z ${POSTGRES_HOST} 5432; do
  sleep 0.1
done
echo "Database is ready!"

export PYTHONPATH=$(pwd)/src:$PYTHONPATH

if [ "$DEVELOPMENT" = "true" ]; then
    echo "Starting FastAPI in development mode..."
    fastapi dev src/api/main.py --host 0.0.0.0 --port 8000
else
    echo "Starting FastAPI in production mode..."
    fastapi run src/api/main.py --host 0.0.0.0 --port 8000
fi
