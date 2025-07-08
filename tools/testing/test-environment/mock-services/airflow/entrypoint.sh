#!/bin/bash
set -e

echo "Starting Test Airflow..."
echo "Environment: ${AIRFLOW__CORE__EXECUTOR:-LocalExecutor}"
echo "Database: ${AIRFLOW__DATABASE__SQL_ALCHEMY_CONN:-not set}"

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! python -c "
import psycopg2
import os
import sys
try:
    # Extract database URL from Airflow config
    db_url = os.environ.get('AIRFLOW__DATABASE__SQL_ALCHEMY_CONN', '')
    if 'postgresql' in db_url:
        # Parse the URL to get connection details
        import re
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', db_url)
        if match:
            user, password, host, port, dbname = match.groups()
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname
            )
            conn.close()
            print('Database is ready!')
        else:
            print('Invalid database URL format')
            sys.exit(1)
    else:
        print('No PostgreSQL database configured')
        sys.exit(1)
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
    echo "Database not ready, waiting..."
    sleep 2
done

# Initialize database
echo "Initializing Airflow database..."
airflow db init

# Create admin user
echo "Creating admin user..."
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin || echo "Admin user already exists"

# Start scheduler in background
echo "Starting Airflow scheduler..."
airflow scheduler &

# Start webserver
echo "Starting Airflow webserver..."
exec airflow webserver --port 8080 --host 0.0.0.0