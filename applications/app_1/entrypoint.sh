#!/bin/bash
export PG_PASSWORD=$(cat /run/secrets/PG_PASS)
python -m streamlit run src/application.py