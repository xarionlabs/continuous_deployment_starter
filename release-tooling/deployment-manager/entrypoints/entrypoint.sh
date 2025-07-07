#!/bin/bash
set -e

# Default entrypoint - just run the release-tool command
exec release-tool "$@"