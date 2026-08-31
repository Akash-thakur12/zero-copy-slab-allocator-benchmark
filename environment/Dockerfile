FROM python:3.11-slim
WORKDIR /app

# Explicitly copy ONLY agent-facing starter files
COPY engine/ /app/engine/
COPY docs/ /app/docs/
COPY samples/ /app/samples/

RUN pip install --no-cache-dir pytest
