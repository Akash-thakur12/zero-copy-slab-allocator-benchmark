#!/bin/bash
set -e
mkdir -p /logs/verifier
mkdir -p verifier
pytest -v -s tests/test_outputs.py
