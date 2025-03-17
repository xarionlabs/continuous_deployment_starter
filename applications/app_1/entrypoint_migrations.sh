#!/bin/bash
export PYTHONPATH=$(pwd)/src:$PYTHONPATH
echo "Running DB MIGRATIONS"
cd src/data/db/migrations/ || { echo "Failed to switch to the migrations directory!!!"; exit 1; }
alembic upgrade head || { echo "Alembic upgrade failed!!!"; exit 1; }
cd -
