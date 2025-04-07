#!/bin/Rscript

args <- commandArgs(trailingOnly = TRUE)

if (length(args) != 3) {
    stop("Expected input: Rscript epigenetic_age_inference.R <sample_sheet_path> <imputed_mynorm_path> <epigenetic_clocks>")
} else {
    sample_sheet_path <- args[1]
    imputed_mynorm_path <- args[2]
    epi_clocks <- unlist(strsplit(args[3], split = ","))
}

library(dnaMethyAge)
library(arrow)
library(dplyr)
library(tidyr)

sample_sheet <- data.frame()
sample_sheet <- read.table(file = sample_sheet_path, sep = ",", dec = ".", header = TRUE)

if (!("Age" %in% colnames(sample_sheet))) {
    stop("Age column containing chronological age for samples not present in sample sheet - epigenetic age cannot be inferred!")
}
if ("PCGrimAge" %in% epi_clocks && !("Sex" %in% colnames(sample_sheet))) {
    stop("Sex column not provided in sample sheet and this info is neccessary for PCGrimAge computation!")
}

imputed_mynorm <- data.frame()
imputed_mynorm <- arrow::read_parquet(imputed_mynorm_path, as_data_frame = TRUE)
imputed_mynorm <- as.data.frame(imputed_mynorm)
rownames(imputed_mynorm) <- imputed_mynorm[, 1]
imputed_mynorm[, 1] <- NULL
imputed_mynorm <- imputed_mynorm[, sample_sheet$Sample_Name]

age_info_frame <- data.frame()
age_info_frame <- sample_sheet %>%
    dplyr::select(Sample_Name, Age) %>%
    dplyr::rename(Sample = Sample_Name)

if ("Sex" %in% colnames(sample_sheet)) {
    age_info_frame <- age_info_frame %>%
        dplyr::mutate(Sex = ifelse(sample_sheet$Sex == "FEMALE", "Female", "Male"))
}

res_list <- list()

for (clock in epi_clocks) {
    res_list[[clock]] <- dnaMethyAge::methyAge(imputed_mynorm, clock = clock, fit_method = "Linear", do_plot = FALSE, age_info = age_info_frame)
    res_list[[clock]] <- res_list[[clock]] %>%
        dplyr::mutate(clock = rep(clock, times = nrow(.)))
}
res_list[["PCGrimAge"]] <- res_list[["PCGrimAge"]] %>%
    dplyr::select(-is_Female)

id_columns <- c()
id_columns <- c("Sample", "Age")

if ("Sex" %in% colnames(sample_sheet)) id_columns <- c(id_columns, "Sex")

res_df <- data.frame()
res_df <- do.call(rbind, res_list)
res_df <- res_df %>%
    tidyr::pivot_wider(
        id_cols = id_columns,
        values_from = c("mAge", "Age_Acceleration"),
        names_from = c("clock")
    )

arrow::write_parquet(res_df, "epi_clocks_res.parquet")
