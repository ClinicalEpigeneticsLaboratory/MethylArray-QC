#!/bin/Rscript

args <- commandArgs(trailingOnly = TRUE)

if (length(args) != 4) {
    stop("Expected input: Rscript ctrl_fluorescence_data.R <idats> <sample_sheet_path> <cpus> <metric>")
} else {
    idats <- args[1]
    sample_sheet_path <- args[2]
    cpus <- args[3]
    metric <- args[4]
}

library(sesame)
library(arrow)
library(glue)
library(stringr)
library(jsonlite)

# problematic: mm285

# Modified controls function from https://github.com/zwdzwd/sesame/
controls_custom <- function(sdf, verbose) {  
    stopifnot(is(sdf, "SigDF"))

    sdf_platform <- character()
    sdf_platform <- sesame::sdfPlatform(sdf, verbose = verbose)

    if (!is.null(attr(sdf, "controls"))) {
        df <- attr(sdf, "controls")
        last_colname <- colnames(df)[ncol(df)]

        # BUG FIX: Fixed a bug when last column name is NA instead of type (which is assigned to another column)
        if(is.na(colnames(df)[ncol(df)])) colnames(df)[ncol(df)] <- "type_str"
        df$Probe_ID <- sapply(
            strsplit(rownames(df), "\\."), 
            function(x) {
                parts <- x[x != ""]
                if(length(parts) > 1) {
                    paste0(paste(parts[-length(parts)], collapse = " "), " (", parts[length(parts)], ")")
                } else {
                    parts
                }
            }
        )
        return(data.frame(Probe_ID = df$Probe_ID, UG = df$G, UR = df$R, Type = df$type_str))
    }
    else if(sesameDataHas(sprintf("%s.address", sdf_platform))) {
        df <- sesameDataGet(sprintf("%s.address", sdf_platform))$controls
        if (is.null(df)) {
            return(sdf[grepl("^ctl", sdf$Probe_ID), ])
        }
        else {
            cbind(
                df, 
                sdf[match(paste0("ctl_", df$Address), sdf$Probe_ID), c("MG", "MR", "UG", "UR")]
            )
        }
    }
    else {
        return(sdf[grepl("^ctl", sdf$Probe_ID), ])
    }
}

extract_control_signals <- function(sdf, sample_name) {

    sdf <- sesame::resetMask(sdf)
    ctl <- controls_custom(sdf)
    ctl$Sample_Name <- sample_name
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

if(!("col" %in% colnames(control_all_df))) {
    control_all_df[, "col"] <- "missing"
}

control_all_df$metric_type <- NA
control_all_df$metric_type <- rep(metric, times = nrow(control_all_df))

metric_fun <- list()
metric_fun <- switch(
    metric,
    "max" = function(i) {
            col <- control_all_df$col[i]
            vals <- switch(col,
                "G" = c(control_all_df$MG[i], control_all_df$UG[i]),
                "R" = c(control_all_df$MR[i], control_all_df$UR[i]),
                "2" = c(control_all_df$MG[i], control_all_df$MR[i], control_all_df$UG[i], control_all_df$UR[i]),
                c(control_all_df$UG[i], control_all_df$UR[i])  # default
        )
        max(vals, na.rm = TRUE)
    },
    "total" = function(i) {
        col <- control_all_df$col[i]
        vals <- switch(col,
            "G" = c(control_all_df$MG[i], control_all_df$UG[i]),
            "R" = c(control_all_df$MR[i], control_all_df$UR[i]),
            "2" = c(control_all_df$MG[i], control_all_df$MR[i], control_all_df$UG[i], control_all_df$UR[i]),
            c(control_all_df$UG[i], control_all_df$UR[i])  # default
        )
        sum(vals, na.rm = TRUE)
    },
    stop("Unsupported metric: ", metric)
)

# Compute the selected metric
control_all_df$metric <- unlist(
    BiocParallel::bplapply(
        seq_len(nrow(control_all_df)),
        metric_fun,
        BPPARAM = BiocParallel::MulticoreParam(cpus)
    )
)

control_all_df$log_10_metric <- NA
control_all_df$log_10_metric <- log10(control_all_df$metric)

if(!("Type" %in% colnames(control_all_df))) {
    control_all_df$Probe_ID_split <- strsplit(as.character(control_all_df$Probe_ID), "_")
    control_all_df$Probe_ID <- sapply(control_all_df$Probe_ID_split, function(x) paste(x[1:2], collapse = "_"))
    control_all_df$Type <- sapply(control_all_df$Probe_ID_split, function(x) ifelse(length(x) > 2, paste(x[3:length(x)], collapse = "_"), NA))
    control_all_df$Probe_ID_split <- NULL
}

control_all_df$Type <- as.character(control_all_df$Type)

arrow::write_parquet(control_all_df, glue("ctrl_fluorescence", ".parquet"))

unique_probe_types_json <- character()
unique_probe_types_json <- toJSON(unique(control_all_df$Type))
write(unique_probe_types_json, "ctrl_unique_probe_types.json")