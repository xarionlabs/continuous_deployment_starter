#!/bin/bash

# Read input from stdin and pass it to jq in the container
docker run --rm -i imega/jq "$@" 