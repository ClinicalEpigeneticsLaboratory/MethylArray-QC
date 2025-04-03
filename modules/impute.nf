process IMPUTE {
    publishDir "${params.output}", mode: 'copy', overwrite: true
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

    script:
    """
    imputation.py ${mynorm} ${p_threshold} ${s_threshold} ${imputer_type}
    """
}
