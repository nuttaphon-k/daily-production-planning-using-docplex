#!/bin/bash

rm -r build
rm -r  dist
rm planner.spec

pyinstaller -F --name planner main.py --noconfirm \
    --add-data "dbconfig.json;." \
    --add-data "cpoptimizer.exe;." \
    --add-data "cplex2211.dll;." \
    --additional-hooks-dir=. \