#!/bin/Rscript

# Portable wrapper around arrow::write_parquet.
#
# On most systems write_parquet writes directly to `path`. On WSL with the
# Nextflow workDir on a Windows NTFS mount (/mnt/c/...), Arrow's memory-mapped
# I/O fails with errno 5 (EIO). When that happens the write is transparently
# retried via a temp file on the container's native Linux filesystem (/tmp),
# which is then copied to the destination with standard buffered I/O.
#
# All other errors are re-thrown unchanged so nothing is swallowed silently.
write_parquet_portable <- function(df, path) {
    tryCatch(
        arrow::write_parquet(df, path),
        error = function(e) {
            if (!grepl("errno 5|Input/output error", conditionMessage(e))) stop(e)
            message("write_parquet: direct write failed with I/O error, retrying via temp file (WSL workaround)...")
            tmp <- tempfile(fileext = ".parquet")
            on.exit(unlink(tmp), add = TRUE)
            arrow::write_parquet(df, tmp)
            if (!file.copy(tmp, path, overwrite = TRUE)) {
                stop(paste0("Failed to copy parquet from '", tmp, "' to '", path, "'. Check disk space and permissions."))
            }
        }
    )
}
