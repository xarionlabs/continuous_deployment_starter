#!/bin/bash
echo "Deploying shopify config"
cd /app/src
npm install -g @shopify/cli@latest
shopify app deploy -f --config $SHOPIFY_CONFIG