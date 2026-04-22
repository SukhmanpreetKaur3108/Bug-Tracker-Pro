#!/usr/bin/env bash
# compile.sh — Compile the C priority engine on Linux / macOS
# Run this once before starting the application.

set -e
echo "Compiling priority_engine.c ..."
gcc -shared -fPIC -o priority_engine.so priority_engine.c -lm
echo "SUCCESS: priority_engine.so created."
