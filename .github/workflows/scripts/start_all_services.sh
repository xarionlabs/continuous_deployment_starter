#!/bin/bash

set -e 

UNITS_DIR="$HOME/.config/containers/systemd"

echo "Reloading unit files..."
systemctl --user daemon-reload

echo "Restarting network services..."
for file in "$UNITS_DIR"/*.network; do
    [ -e "$file" ] || continue
    service_name="$(basename "$file" .network)-network.service"
    echo "Restarting $service_name..."
    systemctl --user restart "$service_name"
done

echo "Restarting volume services..."
for file in "$UNITS_DIR"/*.volume; do
    [ -e "$file" ] || continue
    service_name="$(basename "$file" .volume)-volume.service"
    echo "Restarting $service_name..."
    systemctl --user restart "$service_name"
done

echo "Restarting container services..."
for file in "$UNITS_DIR"/*.container; do
    [ -e "$file" ] || continue
    service_name="$(basename "$file" .container).service"
    echo "Restarting $service_name..."
    systemctl --user restart "$service_name"
done

echo "All Quadlet services restarted successfully."