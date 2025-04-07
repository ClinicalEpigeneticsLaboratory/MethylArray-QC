FROM r-base:4.4.1
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary system dependencies for installing 'dnaMethyAge' and related packages
RUN apt-get update && apt-get install -y \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    gnupg2 \
    lsb-release \
    sudo \
    libgit2-dev \
    libbz2-dev \
    liblzma-dev \
    zlib1g-dev \
    libxt-dev \
    libpng-dev \
    libtiff-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    build-essential \
    && apt-get clean

# Install necessary R packages
RUN R -e "install.packages(c('remotes', 'arrow', 'dplyr', 'tidyr', 'data.table', 'BiocManager'))" \
    && R -e "BiocManager::install('preprocessCore', configure.args = c(preprocessCore = '--disable-threading'), force= TRUE, update=TRUE, type = 'source')" \
    && R -e "remotes::install_github('yiluyucheng/dnaMethyAge', dependencies = TRUE)" \
    && apt-get clean

# Default command to run R
CMD ["R"]
