FROM r-base:4.4.1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
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
    procps \
    && apt-get clean

RUN [ -f /bin/Rscript ] || ln -s /usr/bin/Rscript /bin/Rscript

# Set RSPM as CRAN mirror
RUN echo "options(repos = c(CRAN = 'https://packagemanager.posit.co/cran/latest'))" >> /usr/lib/R/etc/Rprofile.site

# Install CRAN packages (may fall back to source)
RUN R -e "install.packages(c('remotes', 'dplyr', 'tidyr', 'data.table', 'BiocManager'))"

RUN R -e "install.packages('arrow')"

# Install Bioconductor packages
RUN R -e "BiocManager::install('impute', ask = FALSE, update = TRUE)"
RUN R -e "BiocManager::install('preprocessCore', configure.args = '--disable-threading', ask = FALSE, update = TRUE)"

# Install dnaMethyAge from GitHub
RUN R -e "remotes::install_github('yiluyucheng/dnaMethyAge', dependencies = TRUE, upgrade = 'never')"

CMD ["R"]
