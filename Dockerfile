FROM python:3.11-slim
WORKDIR /app
COPY environment/ /app/
RUN pip install --no-cache-dir pytest
