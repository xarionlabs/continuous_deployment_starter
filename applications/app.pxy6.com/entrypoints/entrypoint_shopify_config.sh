#!/bin/bash
echo "Deploying shopify config"
cd /app/src
shopify app deploy -f --config $SHOPIFY_CONFIG