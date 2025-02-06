#!/bin/bash
export PG_PASSWORD=$(cat /run/secrets/pg_password)
python -m streamlit run src/application.py