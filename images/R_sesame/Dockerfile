FROM r-base:4.4.1
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update && apt upgrade -y
RUN apt install build-essential zlib1g-dev libncurses5-dev libgdbm-dev \
        libfontconfig1-dev libcurl4-openssl-dev libharfbuzz-dev libfribidi-dev \
        libnss3-dev libssl-dev libreadline-dev libffi-dev libsqlite3-dev \
        libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev \
        wget libbz2-dev libssl-dev libxml2-dev pandoc openjdk-17-jdk procps -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*

# Install R components
COPY requirements_sesame.R sesame_cache.R ./
RUN Rscript requirements_sesame.R
RUN Rscript sesame_cache.R || echo "Sesame cache error"

# Entrypoint
CMD ["/bin/bash"]