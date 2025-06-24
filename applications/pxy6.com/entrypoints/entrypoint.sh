#!/bin/sh
set -e

# Run database migrations if needed
# npx prisma migrate deploy

# Start the application
exec "$@"
