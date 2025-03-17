#!/bin/bash

CONFIG_DIR="$HOME/.config/containers/systemd"
cd "$CONFIG_DIR" || exit 1

for file in *.service; do
  [[ -e "$file" ]] || continue
  if grep -q "[Service]" "$file" && grep -q "Restart=no" "$file"; then
        sed -i '/\[Service\]/{
            N
            s/\(\[Service\]\n\)Restart=no/\1Type=oneshot\nRemainAfterExit=true/
        }' "$file"
        echo "Updated: $file"
    fi
done

cd - > /dev/null
