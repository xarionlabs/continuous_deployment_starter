#!/bin/bash

export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python -m manage_users

export PGPASSWORD=$POSTGRES_PASSWORD

for file in /app/users.sql/*.sql; do
    if [ -f "$file" ]; then
        echo "Processing $file..."
        # Extract the database name from the file name
        db_name=$(basename "$file" .sql)
        psql -h db -U $POSTGRES_USER -d $db_name -f "$file"
    else
        echo "$file not found!"
    fi
done
