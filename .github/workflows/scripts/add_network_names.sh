#!/bin/bash

CONFIG_DIR="$HOME/.config/containers/systemd"
cd "$CONFIG_DIR" || exit 1

for file in *.network; do
  [[ -e "$file" ]] || continue
  if ! grep -q "^NetworkName=" "$file"; then
    network_name="${file%.network}"
    echo "NetworkName=$network_name" >> "$file"
    echo "Added NetworkName in $file"
  fi
done

cd - > /dev/null
