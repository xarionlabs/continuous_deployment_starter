#!/bin/bash

set -e

UNITS_DIR="$HOME/.config/containers/systemd"

update_unit_partof() {
    local type=$1  # "network", "volume", "container"
    local suffix=$2  # Correct file suffix: ".network", ".volume", ".container"
    local parent_service="all-${type}s.service"

    for service_file in "$UNITS_DIR"/*"${suffix}"; do
        [ -e "$service_file" ] || continue

        # Ensure the service file has a `[Unit]` section
        if ! grep -q "^\[Unit\]" "$service_file"; then
            echo "Adding [Unit] section to $service_file..."
            sed -i "1i [Unit]" "$service_file"
        fi

        # Ensure it contains the correct `PartOf=` directive
        if ! grep -q "PartOf=${parent_service}" "$service_file"; then
            echo "Ensuring $service_file includes PartOf=${parent_service}..."
            sed -i "/^\[Unit\]/a PartOf=${parent_service}" "$service_file"
        fi
    done
}

update_unit_partof "network" ".network"
update_unit_partof "volume" ".volume"
update_unit_partof "container" ".container"

echo "Reloading systemd..."
systemctl --user daemon-reload

echo "All individual services updated successfully."
