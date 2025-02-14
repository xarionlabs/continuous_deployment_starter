#!/bin/bash
echo "::group::$(basename "$0") log"
generate-env-from-gh-variables.sh

echo RUNTIME_UID=${UID} >> .env
echo "::endgroup::"