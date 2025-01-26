#!/bin/Rscript

args = commandArgs(trailingOnly=TRUE)

if (length(args)!=5) {
  stop("Expected input: Rscript preprocess.R <idats> <cpus> <prep_code>")
} else {
  idats = args[1]
  cpus = args[2]
  prep_code = args[3]
  collapse_prefix = args[4]
  collapse_method = args[5]
}

known_prep_codes <- c("QCDPB", "SQCDPB", "TQCDPB", "SQCDPB", "HCDPB", "SHCDPB")
if (!(prep_code %in% known_prep_codes)) {
    stop("Unknown preprocessing code. Use codes predefined in sesame documentation.")
}

known_collapse_methods <- c("mean", "minPval")
if (!(collapse_method %in% known_collapse_methods)) {
    stop("Unknown collapse method. Use method predefined in sesame documentation.")
}

library(sesame)
library(arrow)
library(glue)

message("Parsing ...")
collapse_prefix <- toupper(collapse_prefix) == "TRUE"
mynorm <- openSesame(idats,
                     prep=prep_code,
                     func=getBetas,
                     collapseToPfx=collapse_prefix,
                     collapseMethod=collapse_method,
                     BPPARAM = BiocParallel::MulticoreParam(cpus)
                     )

message("Dumping ...")
mynorm <- as.data.frame(mynorm)
mynorm$CpG <- rownames(mynorm)
write_parquet(mynorm, glue("raw_mynorm", ".parquet"))
