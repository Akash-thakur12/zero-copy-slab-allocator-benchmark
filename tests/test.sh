#!/bin/bash
set -e
mkdir -p /logs/verifier
pytest -v -s tests/test_outputs.py
