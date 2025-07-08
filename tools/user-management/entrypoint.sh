#!/bin/bash

export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python -m manage_users

export PGPASSWORD=$POSTGRES_PASSWORD

echo "Debug: Checking what SQL files were generated..."
ls -la /app/users.sql/ || echo "No users.sql directory found"

echo "Debug: Testing PostgreSQL connection..."
psql -h db -U $POSTGRES_USER -c "SELECT version();" || echo "PostgreSQL connection failed"

echo "Debug: Listing existing databases..."
psql -h db -U $POSTGRES_USER -l

for file in /app/users.sql/*.sql; do
    if [ -f "$file" ]; then
        echo "Processing $file..."
        # Extract the database name from the file name
        db_name=$(basename "$file" .sql)
        # Create the database if it doesn't exist (ignore error if exists)
        echo "Creating database $db_name if it doesn't exist..."
        psql -h db -U $POSTGRES_USER -c "CREATE DATABASE $db_name;" 2>/dev/null || echo "Database $db_name already exists or creation failed"
        
        # Verify database exists before running SQL
        if psql -h db -U $POSTGRES_USER -lqt | cut -d \| -f 1 | grep -qw $db_name; then
            echo "Running SQL script on database $db_name..."
            psql -h db -U $POSTGRES_USER -d $db_name -f "$file"
        else
            echo "ERROR: Database $db_name does not exist and could not be created!"
            exit 1
        fi
    else
        echo "$file not found!"
    fi
done
