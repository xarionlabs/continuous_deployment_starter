#!/bin/bash

if [[ -z "$SECRETS_JSON" || -z "$VARS_JSON" ]]; then
  echo "Error: SECRETS_JSON and VARS_JSON must be provided - check the ssh-action configuration"
  exit 1
fi

ENV_FILE=".env"

> "$ENV_FILE"
echo "$SECRETS_JSON" | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' >> "$ENV_FILE"
echo "$VARS_JSON" | jq -r 'to_entries | .[] | "\(.key)=\(.value)"' >> "$ENV_FILE"

echo "Generated .env file"