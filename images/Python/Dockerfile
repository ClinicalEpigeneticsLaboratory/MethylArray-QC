FROM python:3.12-slim
ENV DEBIAN_FRONTEND=noninteractive

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# procps: required by Nextflow (ps). The remaining packages are WeasyPrint's
# runtime dependencies (Pango text layout + libffi for cffi) plus fonts, needed to
# render the PDF report (params.output_format = "pdf"). Kaleido (pinned to 0.2.1 in
# pyproject.toml) bundles its own headless renderer, so no browser is installed here.
RUN apt update && apt upgrade -y &&  \
    apt install -y --no-install-recommends \
        procps \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libffi8 \
        fontconfig \
        fonts-liberation \
        fonts-dejavu-core \
        shared-mime-info && \
    apt clean && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN python -m pip install --no-cache-dir poetry poetry-plugin-export
RUN python -m poetry export --without-hashes --format=requirements.txt -o requirements.txt
RUN python -m pip install -r requirements.txt

# Entrypoint
CMD ["/bin/bash"]