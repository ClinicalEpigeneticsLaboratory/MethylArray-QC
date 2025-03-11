#!/bin/Rscript

args = commandArgs(trailingOnly=TRUE)

if (length(args)!=3) {
  stop("Expected input: Rscript QC.R <idats> <cpus> <sample_list>")
} else {
  idats = args[1]
  cpus = args[2]
  sample_sheet_path = args[3]
}

library(sesame)
library(arrow)
library(glue)

message("Parsing ...")

sample_sheet <- data.frame()
sample_sheet <- read.csv(file = sample_sheet_path, sep = ",", dec = ".", quote = "")

#print(idats)
#print(sample_sheet)

sample_list_dir <- list()
sample_list_dir <- file.path(idats, sample_sheet$Array_Position)
print(sample_list_dir)
print(typeof(sample_list_dir))


sdfs <- lapply(sample_list_dir, FUN = readIDATpair, manifest = NULL, platform = "", min_beads = NULL, controls = NULL, verbose = FALSE)
qcs <- openSesame(sdfs, prep="", func=sesameQC_calcStats, BPPARAM = BiocParallel::MulticoreParam(cpus))

message("QC ...")
quality_metrics <- do.call(rbind, lapply(qcs, as.data.frame))

message("Dumping ...")
quality_metrics$Sample <- rownames(quality_metrics)
write_parquet(quality_metrics, glue("qc", ".parquet"))
