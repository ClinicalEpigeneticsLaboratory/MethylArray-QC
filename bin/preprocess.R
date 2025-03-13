#!/bin/Rscript

args = commandArgs(trailingOnly=TRUE)

if (length(args)!=6) {
  stop("Expected input: Rscript preprocess.R <idats> <cpus> <prep_code> <sample_sheet_path>")
} else {
  idats = args[1]
  cpus = args[2]
  prep_code = args[3]
  collapse_prefix = args[4]
  collapse_method = args[5]
  sample_sheet_path = args[6]
}

# To discuss: remove redundant parameter validation?
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

sample_sheet <- data.frame()
sample_sheet <- read.csv(file = sample_sheet_path, sep = ",", dec = ".", quote = "")

sample_list_dir <- list()
sample_list_dir <- file.path(idats, sample_sheet$Array_Position)

sdfs <- lapply(sample_list_dir, FUN = readIDATpair, manifest = NULL, platform = "", min_beads = NULL, controls = NULL, verbose = FALSE)
if(length(sdfs) < nrow(sample_sheet)) stop(paste0("IDATs for ", nrow(sample_sheet) - length(sdfs)), " samples are missing!")

mynorm <- openSesame(sdfs,
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
