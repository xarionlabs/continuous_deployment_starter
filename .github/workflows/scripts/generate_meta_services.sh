#!/bin/bash
echo "::group::$(basename "$0") log"
set -e
trap 'echo "::endgroup::"; echo "❌ $(basename "$0") failed!"' EXIT

UNITS_DIR="$HOME/.config/containers/systemd"
SYSTEMD_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNITS_DIR"
mkdir -p "$SYSTEMD_DIR"

generate_meta_service() {
    local type=$1  # "network", "volume", "container"
    local suffix=$2  # Naming suffix: "-network", "-volume", or "" for containers
    local meta_service="$SYSTEMD_DIR/all-${type}s.service"
    local services_list=()

    for file in "$UNITS_DIR"/*."$type"; do
        [ -e "$file" ] || continue
        base_name="$(basename "$file" ."$type")"
        service_name="${base_name}${suffix}.service"
        services_list+=("$service_name")
    done

    if [ ${#services_list[@]} -eq 0 ]; then
        echo "No $type services found, removing $meta_service if it exists."
        rm -f "$meta_service"
        return
    fi

    echo "Generating $meta_service..."

    cat > "$meta_service" <<EOF
[Unit]
Description=Service to manage all $type services
EOF

    echo "Requires=${services_list[*]}" >> "$meta_service"
    echo "After=${services_list[*]}" >> "$meta_service"

    cat >> "$meta_service" <<EOF

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=true

[Install]
WantedBy=default.target
EOF
}

generate_meta_service "network" "-network"
generate_meta_service "volume" "-volume"
generate_meta_service "container" ""

NETWORKS_SERVICE="$SYSTEMD_DIR/all-networks.service"
VOLUMES_SERVICE="$SYSTEMD_DIR/all-volumes.service"
CONTAINERS_SERVICE="$SYSTEMD_DIR/all-containers.service"
CONTAINER_SERVICES=()

for file in "$UNITS_DIR"/*.container; do
    [ -e "$file" ] || continue
    base_name="$(basename "$file" .container)"
    service_name="${base_name}.service"
    CONTAINER_SERVICES+=("$service_name")
done

echo "Generating $CONTAINERS_SERVICE..."
cat > "$CONTAINERS_SERVICE" <<EOF
[Unit]
Description=Service to manage all container services
EOF

REQUIRES_LIST=()
AFTER_LIST=()

if [ -e "$NETWORKS_SERVICE" ]; then
    REQUIRES_LIST+=("all-networks.service")
    AFTER_LIST+=("all-networks.service")
fi

if [ -e "$VOLUMES_SERVICE" ]; then
    REQUIRES_LIST+=("all-volumes.service")
    AFTER_LIST+=("all-volumes.service")
fi

if [ ${#CONTAINER_SERVICES[@]} -gt 0 ]; then
    REQUIRES_LIST+=("${CONTAINER_SERVICES[@]}")
fi

if [ ${#REQUIRES_LIST[@]} -gt 0 ]; then
    echo "Requires=${REQUIRES_LIST[*]}" >> "$CONTAINERS_SERVICE"
fi

if [ ${#AFTER_LIST[@]} -gt 0 ]; then
    echo "After=${AFTER_LIST[*]}" >> "$CONTAINERS_SERVICE"
fi

cat >> "$CONTAINERS_SERVICE" <<EOF

[Service]
Type=oneshot
ExecStart=/bin/true
RemainAfterExit=true

[Install]
WantedBy=default.target
EOF

echo "Reloading systemd..."
systemctl --user daemon-reload

echo "All systemd meta-services generated successfully."
echo "::endgroup::"