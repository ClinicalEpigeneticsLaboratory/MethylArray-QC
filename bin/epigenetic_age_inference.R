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

source(file.path(dirname(normalizePath(sub("--file=", "", commandArgs(FALSE)[grep("--file=", commandArgs(FALSE))]))), "r_utils.R"))

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

if("PCGrimAge" %in% epi_clocks) {
    res_list[["PCGrimAge"]] <- res_list[["PCGrimAge"]] %>%
        dplyr::select(-is_Female)
}

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

write_parquet_portable(res_df, "epi_clocks_res.parquet")

# Write results as NDJSON (one JSON object per line) using base R.
# arrow::write_json_arrow is not available in the Docker image's arrow version.
# load_table_data_ndjson in report.py parses this format line-by-line.
col_is_numeric <- vapply(res_df, is.numeric, logical(1))

json_value <- function(x, is_num) {
    if (is.na(x) || (is_num && is.infinite(x))) return("null")
    if (is_num) return(as.character(x))
    s <- gsub("\\\\", "\\\\\\\\", as.character(x))  # escape \ -> \\
    s <- gsub('"', '\\"', s)                          # escape " -> \"
    paste0('"', s, '"')
}

rows_ndjson <- vapply(seq_len(nrow(res_df)), function(i) {
    pairs <- mapply(
        function(col, is_num) sprintf('"%s":%s', col, json_value(res_df[[col]][i], is_num)),
        names(res_df), col_is_numeric,
        SIMPLIFY = TRUE
    )
    paste0("{", paste(pairs, collapse = ","), "}")
}, character(1))

writeLines(rows_ndjson, "epi_clocks_res.json")