process IMPUTE {
    publishDir "${params.output}", mode: 'copy', overwrite: true
    label 'python'

    input:
    path mynorm
    val p_threshold
    val s_threshold
    val imputer_type

    output:
    path "imputed_mynorm.parquet"
    path "impute_nan_per_sample.json"
    path "impute_nan_per_probe.json"

    script:
    """
    imputation.py ${mynorm} ${p_threshold} ${s_threshold} ${imputer_type}
    """
}
