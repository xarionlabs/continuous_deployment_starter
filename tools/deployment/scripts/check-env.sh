#!/bin/bash

if [[ -z "$1" ]]; then
    echo "Usage: $0 <docker-compose-file>"
    exit 1
fi

compose_file="$1"

if [[ ! -f "$compose_file" ]]; then
    echo "Error: File '$compose_file' not found!"
    exit 1
fi

missing=0
while read -r var; do
    if [[ -z "${!var}" ]]; then
        echo "❗️Missing variable: $var"
        missing=1
    fi
done < <(grep -oE '\$\{[A-Z0-9_]+\}' "$compose_file" | sed 's/[${}]//g' | sort -u)

if [[ "$missing" -eq 1 ]]; then
    exit 1
else
    echo "All variables are set"
fi
