FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt update && apt upgrade -y &&  \
    apt clean && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN python -m pip install --no-cache-dir poetry poetry-plugin-export
RUN python -m poetry export --without-hashes --format=requirements.txt -o requirements.txt
RUN python -m pip install -r requirements.txt

# Entrypoint
CMD ["/bin/bash"]