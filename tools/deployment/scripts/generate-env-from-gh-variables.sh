#!/bin/bash

if [[ -z "$VARS_JSON" ]]; then
  echo "Error: VARS_JSON must be provided - check the ssh-action configuration"
  exit 1
fi

ENV_FILE=".env"

> "$ENV_FILE"
echo "$VARS_JSON" | sed s/\[\",\ \}\{\]//g | sed s/:/=/ | grep -v '^$' >> "$ENV_FILE" 2>/dev/null || true

echo "Generated .env file"