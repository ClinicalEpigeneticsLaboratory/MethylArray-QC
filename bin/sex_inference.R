#!/bin/Rscript

args = commandArgs(trailingOnly=TRUE)

if (length(args)!=3) {
    stop("Expected input: Rscript sex_inference.R <imputed_mynorm_path> <cpus> <sample_sheet_path>")
} else {
    imputed_mynorm_path = args[1]
    cpus = args[2]
    sample_sheet_path = args[3]
}

library(sesame)
library(arrow)
library(glue)

sample_sheet <- data.frame()
sample_sheet <- read.csv(file = sample_sheet_path, sep = ",", dec = ".", quote = "")

if(!("Sex" %in% colnames(sample_sheet))) stop("Declared sex (column: Sex) not provided in sample sheet!")

imputed_mynorm <- data.frame()
imputed_mynorm <- read_parquet(imputed_mynorm_path, as_data_frame = TRUE)

cg_list <- c()

if("CpG" %in% colnames(imputed_mynorm)) {

    cg_list <- imputed_mynorm$CpG
    imputed_mynorm <- as.data.frame(imputed_mynorm)
    rownames(imputed_mynorm) <- imputed_mynorm$CpG
    imputed_mynorm$CpG <- NULL
} else {
    cg_list <- rownames(imputed_mynorm)
}

imp_mynorm_platform <- character()
imp_mynorm_platform <- sesameData::inferPlatformFromProbeIDs(cg_list, silent = TRUE)

imputed_mynorm <- imputed_mynorm[, sample_sheet$Sample_Name]
imputed_mynorm <- as.matrix(imputed_mynorm)

inferred_sex <- list()
inferred_sex <- BiocParallel::bplapply(
    X = sample_sheet$Sample_Name,
    FUN = function(x, imputed_mynorm, imp_mynorm_platform) {
        sesame::inferSex(imputed_mynorm[, x], platform = imp_mynorm_platform)
    },
    imputed_mynorm = imputed_mynorm,
    imp_mynorm_platform = imp_mynorm_platform,
    BPPARAM = BiocParallel::MulticoreParam(cpus)
)

write(
    jsonlite::toJSON(
        data.frame(
            Sample_Name = sample_sheet$Sample_Name,
            Declared_sex = sample_sheet$Sex,
            Inferred_sex = unlist(inferred_sex),
            Sex_equal = sample_sheet$Sex == unlist(inferred_sex)
        ), 
        pretty = TRUE
    ),
    glue("inferred_sex", ".json")
)