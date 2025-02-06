#!/bin/bash

CONFIG_DIR="$HOME/.config/containers/systemd"
cd "$CONFIG_DIR" || exit 1

for file in *.volume; do
  [[ -e "$file" ]] || continue
  if ! grep -q "^VolumeName=" "$file"; then
    network_name="${file%.network}"
    echo "Volume=$network_name" >> "$file"
    echo "Added Volume in $file"
  fi
done

cd - > /dev/null
