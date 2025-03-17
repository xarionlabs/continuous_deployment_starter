#!/bin/bash

export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python -m manage_users
export PGPASSWORD=$POSTGRES_PASSWORD

if [ ! -f /app/users.sql ]; then
    echo "users.sql file not found!"
    exit 1
fi

psql -h db -U $POSTGRES_USER -f /app/users.sql