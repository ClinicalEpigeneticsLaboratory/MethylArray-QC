options(Ncpus = 10)

install.packages(c("devtools", "arrow", "jsonlite", "htmlwidgets", "ggplot2", "plotly", "BiocManager", "remotes"))

BiocManager::install("preprocessCore", configure.args = c(preprocessCore = "--disable-threading"), force=TRUE, update=TRUE, type = "source")
BiocManager::install(c("minfi", "Rsamtools", "RnBeads", "illuminaio", "nullranges"))
BiocManager::install("sesame")
