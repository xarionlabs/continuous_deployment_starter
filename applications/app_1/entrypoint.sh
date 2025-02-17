#!/bin/bash
export PG_PASSWORD=$(cat /run/secrets/PG_PASS)
python -m streamlit run --server.headless true --server.port 8080 src/application.py