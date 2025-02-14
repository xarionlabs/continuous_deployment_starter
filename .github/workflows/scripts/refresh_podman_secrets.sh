#!/bin/bash
echo "::group::$(basename "$0") log"
set -e
trap 'EXIT_CODE=$?; echo "::endgroup::"; if [ $EXIT_CODE -ne 0 ]; then echo "❌ $(basename "$0") failed!"; else echo "✅ $(basename "$0") succeeded!"; fi' EXIT

SECRETS_JSON="$1"

if [[ -z "SECRETS_JSON" ]]; then
    echo "Usage: $0 <repo> <github_token>"
    exit 1
fi


EXISTING_SECRETS=$(podman secret ls --format '{{.Name}}')
if [[ -n "$EXISTING_SECRETS" ]]; then
    echo "Removing existing Podman secrets..."
    echo "$EXISTING_SECRETS" | xargs -n1 podman secret rm || true
fi

PARSED_SECRETS=$(jq -r 'to_entries|map("\(.key)=\(.value|@json)")|.[]' <<< "$SECRETS_JSON")

if [[ -z "PARSED_SECRETS" ]]; then
    echo "No GitHub secrets found in $REPO."
    exit 1
fi

echo "Adding secrets to Podman..."
while IFS= read -r SECRET_ROW; do
    SECRET_NAME=$(echo "$SECRET_ROW" | cut -d '=' -f 1)
    VALUE=$(echo "$SECRET_ROW" | cut -d '=' -f 2- | jq -r .)
     echo -n "$VALUE" | podman secret create "$SECRET_NAME" -
     echo "Created Podman secret: $SECRET_NAME"
done <<< "$PARSED_SECRETS"

echo "::endgroup::"
echo "Done!"
