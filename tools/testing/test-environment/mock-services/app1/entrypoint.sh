#!/bin/bash
set -e

echo "Starting Test App 1..."
echo "Environment: ${ENVIRONMENT:-test}"
echo "Database URL: ${DATABASE_URL:-not set}"

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done

# Start Streamlit in background
echo "Starting Streamlit app..."
streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true &

# Start FastAPI
echo "Starting FastAPI server..."
exec python main.py