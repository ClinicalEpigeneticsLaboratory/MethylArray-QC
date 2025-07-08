process IMPUTE {
    publishDir "${params.output}/Imputation", mode: 'copy', overwrite: true
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/Imputation"
    label 'python'

    input:
    path mynorm
    val p_threshold
    val s_threshold
    val imputer_type

    output:
    path "imputed_mynorm.parquet", emit: imputed_mynorm
    path "impute_nan_per_sample.parquet", emit: nan_per_sample
    path "impute_nan_per_probe.parquet", emit: nan_per_probe
    path "imputation_summary.json", emit: imputation_summary_path

    script:
    """
    imputation.py ${mynorm} ${p_threshold} ${s_threshold} ${imputer_type}
    """
}
