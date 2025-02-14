#!/bin/bash

set -e

SYSTEMD_DIR="$HOME/.config/systemd/user"
UNITS_DIR="$HOME/.config/containers/systemd"

echo "Restarting all container services..."
systemctl --user restart all-containers.service

echo "Checking service statuses..."

SERVICE_FILES=("all-containers.service")

for type in container network volume; do
    for file in "$UNITS_DIR"/*."$type"; do
        [ -e "$file" ] || continue
        base_name="$(basename "$file" ."$type")"

        case "$type" in
            container) service_name="$base_name.service" ;;
            network) service_name="$base_name-network.service" ;;
            volume) service_name="$base_name-volume.service" ;;
        esac

        SERVICE_FILES+=("$service_name")
    done
done

FAILED_SERVICES=()

for service in "${SERVICE_FILES[@]}"; do
    TYPE=$(systemctl --user show -p Type --value "$service" || true)

    if [ "$TYPE" == "oneshot" ]; then
        STATUS=$(systemctl --user show -p Result --value "$service" || true)
        if [ "$STATUS" != "success" ]; then
            echo "❌ $service did NOT exit successfully (Status: $STATUS)"
            FAILED_SERVICES+=("$service")
        else
            echo "✅ $service ran successfully."
        fi
    else
        STATUS=$(systemctl --user show -p ActiveState --value "$service" || true)
        if [ "$STATUS" != "active" ]; then
            echo "❌ $service is NOT running (Status: $STATUS)"
            FAILED_SERVICES+=("$service")
        else
            echo "✅ $service is running."
        fi
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
