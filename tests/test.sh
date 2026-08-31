#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p /logs/verifier
mkdir -p "$SCRIPT_DIR/../verifier"
pytest -v -s "$SCRIPT_DIR/test_outputs.py"
