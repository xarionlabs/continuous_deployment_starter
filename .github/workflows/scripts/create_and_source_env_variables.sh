#!/bin/bash

generate-env-from-gh-variables.sh

echo UID=${UID} >> env.sh

set -o allexport
source services/version.env
source .env
set +o allexport
