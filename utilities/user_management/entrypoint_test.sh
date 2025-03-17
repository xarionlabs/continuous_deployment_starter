#!/bin/bash
./entrypoint.sh
export PYTHONPATH=$PYTHONPATH:./src/
pytest