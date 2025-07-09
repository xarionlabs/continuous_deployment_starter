#!/bin/bash
echo "Starting app..."

export DATABASE_PROVIDER="postgresql"
export DATABASE_URL="postgresql://pxy6:${PSQL_APP_PXY6_PASSWORD}@db:5432/pxy6"

cd /app/src
npm run docker-start