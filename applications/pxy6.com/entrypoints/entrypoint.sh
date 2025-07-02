#!/bin/sh
set -e

# Run database migrations if needed
# npx prisma migrate deploy
npm run build

# Start the application
exec "$@"
