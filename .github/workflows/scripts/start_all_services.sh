#!/bin/bash
set -euo pipefail

echo "::group::$(basename "$0") log"

SYSTEMD_DIR="$HOME/.config/systemd/user"
UNITS_DIR="$HOME/.config/containers/systemd"

# Function to check if a service exists
service_exists() {
    systemctl --user list-unit-files | grep -q "^$1"
}

# Function to get service dependencies
get_service_dependencies() {
    systemctl --user list-dependencies "$1" --plain | grep -v "^$1$" || true
}

# Function to check service status
check_service_status() {
    local service="$1"
    local type=$(systemctl --user show -p Type --value "$service" || true)
    local status
    local max_retries=3
    local retry_count=0

    if [ "$type" == "oneshot" ]; then
        status=$(systemctl --user show -p Result --value "$service" || true)
        if [ "$status" != "success" ]; then
            echo "❌ $service failed to execute successfully (Status: $status)"
            echo "⏳ Waiting 5 seconds to allow for potential recovery..."
            sleep 5
            # Check status again after wait
            status=$(systemctl --user show -p Result --value "$service" || true)
            if [ "$status" != "success" ]; then
                return 1
            fi
            echo "✅ $service recovered after wait"
        fi
    else
        while true; do
            status=$(systemctl --user show -p ActiveState --value "$service" || true)
            
            case "$status" in
                "active")
                    echo "✅ $service is running successfully"
                    return 0
                    ;;
                "deactivating"|"activating")
                    if [ $retry_count -ge $max_retries ]; then
                        echo "❌ $service is stuck in $status state after $max_retries retries"
                        return 1
                    fi
                    echo "⏳ $service is $status, waiting 5 seconds (attempt $((retry_count + 1))/$max_retries)..."
                    sleep 5
                    retry_count=$((retry_count + 1))
                    ;;
                *)
                    if [ $retry_count -ge $max_retries ]; then
                        echo "❌ $service is not running (Status: $status)"
                        return 1
                    fi
                    echo "⏳ $service is not running (Status: $status), waiting 5 seconds (attempt $((retry_count + 1))/$max_retries)..."
                    sleep 5
                    retry_count=$((retry_count + 1))
                    ;;
            esac
        done
    fi
    return 0
}

echo "Reloading systemd..."
systemctl --user daemon-reload

# Collect all service files
SERVICE_FILES=()
for type in container network volume; do
    for file in "$UNITS_DIR"/*."$type"; do
        [ -e "$file" ] || continue
        base_name="$(basename "$file" ."$type")"

        case "$type" in
            container) service_name="$base_name.service" ;;
            network) service_name="$base_name-network.service" ;;
            volume) service_name="$base_name-volume.service" ;;
        esac

        if service_exists "$service_name"; then
            SERVICE_FILES+=("$service_name")
        fi
    done
done

echo "Starting all services via all-containers.service..."
if ! systemctl --user start all-containers.service; then
    echo "❌ Failed to start all-containers.service"
    echo "🔻 Service logs:"
    journalctl --user -u all-containers.service --no-pager --lines=20 | tail -n 20
    exit 1
fi

echo "Checking service statuses in dependency order..."
echo "::endgroup::"

# Get the dependency order for all services
DEPENDENCY_ORDER=()
for service in "${SERVICE_FILES[@]}"; do
    if ! service_exists "$service"; then
        continue
    fi
    # Get dependencies and add them to the order if not already present
    while read -r dep; do
        if [[ ! " ${DEPENDENCY_ORDER[@]} " =~ " ${dep} " ]]; then
            DEPENDENCY_ORDER+=("$dep")
        fi
    done < <(get_service_dependencies "$service")
    # Add the service itself if not already present
    if [[ ! " ${DEPENDENCY_ORDER[@]} " =~ " ${service} " ]]; then
        DEPENDENCY_ORDER+=("$service")
    fi
done

FAILED_SERVICES=()
for service in "${DEPENDENCY_ORDER[@]}"; do
    if ! service_exists "$service"; then
        continue
    fi

    if ! check_service_status "$service"; then
        FAILED_SERVICES+=("$service")
    fi
done

if [ ${#FAILED_SERVICES[@]} -gt 0 ]; then
    echo -e "\n🔴 Some services failed to start properly:"
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "\n🔻 Detailed logs for $service:"
        journalctl --user -u "$service" --no-pager --lines=50 | tail -n 50
    done
    exit 1
else
    echo "🎉 All services are running correctly!"
    exit 0
fi

