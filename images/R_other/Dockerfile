FROM r-base:4.4.1
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies for installing 'meffonym'
RUN apt-get update && apt-get install -y \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    gnupg2 \
    lsb-release \
    sudo \
    && apt-get clean

# Install 'meffonym' R package using remotes
RUN R -e "install.packages('remotes')" \
    && R -e "remotes::install_github('perishky/meffonym')" \
    && apt-get clean

# Default command to run R
CMD ["R"]