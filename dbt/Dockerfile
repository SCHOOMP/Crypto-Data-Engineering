FROM python:3.11-slim

ENV DBT_PROFILES_DIR=/dbt

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /dbt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
