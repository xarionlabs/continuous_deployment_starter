#!/bin/bash

set -e

SYSTEMD_DIR="$HOME/.config/systemd/user"
UNITS_DIR="$HOME/.config/containers/systemd"

echo "Restarting all container services..."
systemctl --user restart all-containers.service

echo "Checking service statuses..."

SERVICE_FILES=("$SYSTEMD_DIR"/all-containers.service)

for type in container network volume; do
    for file in "$UNITS_DIR"/*."$type"; do
        [ -e "$file" ] || continue
        service_name="$(basename "$file" ."$type").service"
        SERVICE_FILES+=("$service_name")
    done
done

FAILED_SERVICES=()

for service in "${SERVICE_FILES[@]}"; do
    STATUS=$(systemctl --user is-active "$service" || true)

    if [ "$STATUS" != "active" ]; then
        echo "❌ $service is NOT running (Status: $STATUS)"
        FAILED_SERVICES+=("$service")
    else
        echo "✅ $service is running."
    fi
done

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "\n🔴 Fetching logs for failed services..."
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "\n🔻 Logs for $service:"
        journalctl --user -u "$service" --no-pager --lines=20 | tail -n 20
    done
else
    echo "🎉 All services are running correctly!"
fi
