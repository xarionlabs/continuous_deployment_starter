#!/bin/bash

set -e  # Exit on any error

REPO="$1"       # GitHub repository (e.g., "org/repo")
GH_TOKEN="$2"   # GitHub token for authentication
DEPLOYMENT="$3" # Deployment Environment to sync secrets from
if [[ -z "$REPO" || -z "$GH_TOKEN" ]]; then
    echo "Usage: $0 <repo> <github_token>"
    exit 1
fi


echo "Logging into GitHub CLI to pull in secrets..."
gh auth login --with-token <<< "$GH_TOKEN"


echo "Syncing secrets from GitHub repo: $REPO"

# Remove all existing Podman secrets
EXISTING_SECRETS=$(podman secret ls --format '{{.Name}}')
if [[ -n "$EXISTING_SECRETS" ]]; then
    echo "Removing existing Podman secrets..."
    echo "$EXISTING_SECRETS" | xargs -n1 podman secret rm || true
fi

# Fetch secrets from GitHub
SECRETS=$(gh secret list --repo "$REPO" --env "$DEPLOYMENT" | awk '{print $1}')

if [[ -z "$SECRETS" ]]; then
    echo "No GitHub secrets found in $REPO."
    exit 1
fi

echo "Adding secrets to Podman..."

for SECRET in $SECRETS; do
    VALUE=$(gh secret get "$SECRET" --repo "$REPO" --env "$DEPLOYMENT" )
    SECRET_NAME=$(echo "$SECRET" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9_' '_')

    # Create new secret
    echo -n "$VALUE" | podman secret create "$SECRET_NAME" -
    echo "Created Podman secret: $SECRET_NAME"
done

gh auth logout

echo "Done!"
