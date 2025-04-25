#!/bin/Rscript

args <- commandArgs(trailingOnly = TRUE)

if (length(args) != 3) {
    stop("Expected input: Rscript ctrl_fluorescence_data.R <idats> <sample_sheet_path> <cpus>")
} else {
    idats <- args[1]
    sample_sheet_path <- args[2]
    cpus <- args[3]
}

library(sesame)
library(arrow)
library(glue)

extract_control_signals <- function(sdf, sample_name) {
    ctl <- sesame::controls(sdf)
    ctl$Sample <- sample_name
    ctl
}

sample_sheet <- data.frame()
sample_sheet <- read.csv(file = sample_sheet_path, sep = ",", dec = ".", quote = "")

sample_list_dir <- list()
sample_list_dir <- file.path(idats, sample_sheet$Array_Position)

sdfs <- BiocParallel::bplapply(
    sample_list_dir, 
    FUN = readIDATpair, 
    BPPARAM = BiocParallel::MulticoreParam(cpus)
)
if (length(sdfs) < nrow(sample_sheet)) stop(paste0("IDATs for ", nrow(sample_sheet) - length(sdfs)), " samples are missing!")
names(sdfs) <- sample_sheet$Sample_Name

control_all <- list()
control_all <- tryCatch(
    {
        lapply(
            seq_len(length(sdfs)), 
            function(x, sdfs) {
                extract_control_signals(sdf = sdfs[[x]], sample_name = names(sdfs)[x])
            },
            sdfs = sdfs
        )
    },
    error = function(cond) {
        message(paste("Array type: ", sesame::sdfPlatform(sdfs[[1]])))
        message("Here's the original error message:")
        message(conditionMessage(cond))
    }
)

control_all_df <- data.frame()
control_all_df <- do.call(rbind, control_all)

control_all_df$Probe_ID_split <- strsplit(as.character(control_all_df$Probe_ID), "_")

control_all_df$max_intensity <- NA
control_all_df$max_intensity <- unlist(
    BiocParallel::bplapply(
        seq_len(nrow(control_all_df)), 
        function(i) {
            col <- control_all_df$col[i]
            if (col == "G") {
                max(control_all_df$MG[i], control_all_df$UG[i], na.rm = TRUE)
            } else if (col == "R") {
                max(control_all_df$MR[i], control_all_df$UR[i], na.rm = TRUE)
            } else if (col == "2") {
                max(control_all_df$MG[i], control_all_df$MR[i], control_all_df$UG[i], control_all_df$UR[i], na.rm = TRUE)
            } else {
                NA # fallback if 'col' is unexpected
            }
        },
        BPPARAM = BiocParallel::MulticoreParam(cpus)
    )
)

control_all_df$Probe_ID <- sapply(control_all_df$Probe_ID_split, function(x) paste(x[1:2], collapse = "_"))

control_all_df$Control_Type <- sapply(control_all_df$Probe_ID_split, function(x) ifelse(length(x) > 2, paste(x[3:length(x)], collapse = "_"), NA))

control_all_df$Probe_ID_split <- NULL

arrow::write_parquet(control_all_df, glue("ctrl_fluorescence", ".parquet"))
