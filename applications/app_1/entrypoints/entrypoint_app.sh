#!/bin/bash
set -e

echo "Waiting for database to be ready..."
while ! nc -z ${POSTGRES_HOST} 5432; do
  sleep 0.1
done
echo "Database is ready!"

export PYTHONPATH=$(pwd)/src:$PYTHONPATH

if [ "$DEVELOPMENT" = "true" ]; then
    echo "Starting Streamlit in development mode..."
    streamlit run src/app/main.py --server.headless true --server.port 8080 --server.address 0.0.0.0 --server.runOnSave true
else
    echo "Starting Streamlit in production mode..."
    streamlit run src/app/main.py --server.headless true --server.port 8080 --server.address 0.0.0.0
fi 