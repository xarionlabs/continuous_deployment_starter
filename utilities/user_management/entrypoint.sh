#!/bin/bash
#
export PYTHONPATH=$(pwd)/src:$PYTHONPATH
python -m manage_users
export PGPASSWORD=$POSTGRES_PASSWORD
psql -h db -U postgres -f /app/users.sql