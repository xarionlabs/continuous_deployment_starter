#!/bin/bash

echo "::group::$(basename "$0") log"

# Fix auto-update labels that get converted incorrectly by podlet
echo "Fixing AutoUpdate=registry to Label=io.containers.autoupdate=registry in quadlet files..."

for file in ~/.config/containers/systemd/*.container; do
  if [ -f "$file" ]; then
    # Check if the file contains AutoUpdate=registry
    if grep -q "^AutoUpdate=registry$" "$file"; then
      echo "Fixing autoupdate label in $(basename "$file")"
      # Replace AutoUpdate=registry with Label=io.containers.autoupdate=registry
      sed -i 's/^AutoUpdate=registry$/Label=io.containers.autoupdate=registry/' "$file"
    fi
  fi
done

echo "Autoupdate label fixes completed"
echo "::endgroup::"