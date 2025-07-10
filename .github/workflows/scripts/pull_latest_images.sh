#!/bin/bash

CONFIG_DIR="$HOME/.config/containers/systemd"
cd "$CONFIG_DIR" || exit 1

for file in *.container; do
  [[ -e "$file" ]] || continue
  if grep -q '^Image=' "$file"; then
    image=$(grep '^Image=' "$file" | cut -d'=' -f2)
    echo "Pulling $image"
    if ! podman pull "$image"; then
      echo "⚠️  Failed to pull $image - continuing with existing image"
    else
      echo "✅ Successfully pulled $image"
    fi
  fi
done

cd - > /dev/null