#!/bin/Rscript

args = commandArgs(trailingOnly=TRUE)

if (length(args)!=2) {
  stop("Expected input: Rscript QC.R <idats> <cpus>")
} else {
  idats = args[1]
  cpus = args[2]
}

library(sesame)
library(arrow)
library(glue)

message("Parsing ...")
qcs <- openSesame(idats, prep="", func=sesameQC_calcStats, BPPARAM = BiocParallel::MulticoreParam(cpus))

message("QC ...")
quality_metrics <- do.call(rbind, lapply(qcs, as.data.frame))

message("Dumping ...")
quality_metrics$Sample <- rownames(quality_metrics)
write_parquet(quality_metrics, glue("qc", ".parquet"))
