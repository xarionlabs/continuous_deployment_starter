#!/bin/bash

CONFIG_DIR="$HOME/.config/containers/systemd"
cd "$CONFIG_DIR" || exit 1

for file in *.container; do
  [[ -e "$file" ]] || continue
  if grep -q '^Secret=' "$file"; then
    sed -i '/^Secret=/ s/$/,type=env/' "$file"
    echo "Updated Secrets in $file"
  fi
done

cd - > /dev/null
