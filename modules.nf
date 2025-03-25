process QC {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'qc.parquet'
    label 'r'

    input:
    path idats
    val cpus
    path sample_sheet_path

    output:
    path "qc.parquet"

    script:
    """
    QC.R $idats $cpus $sample_sheet_path
    """
}

process preprocess {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'raw_mynorm.parquet'
    label 'r'

    input:
    path idats
    val cpus
    val prep_code
    val collapse_prefix
    val collapse_prefix_method
    path sample_sheet_path

    output:
    path "raw_mynorm.parquet"

    script:
    """
    preprocess.R $idats $cpus $prep_code $collapse_prefix $collapse_prefix_method $sample_sheet_path
    """
}

process impute {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'imputed_mynorm.parquet'
    label 'python'

    input:
    path mynorm
    val p_threshold
    val s_threshold
    val imputer_type

    output:
    path "imputed_mynorm.parquet"

    script:
    """
    imputation.py $mynorm $p_threshold $s_threshold $imputer_type
    """
}

process anomaly_detection {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'ao_results.parquet'
    label 'python'

    input:
    path mynorm

    output:
    path "ao_results.parquet"

    script:
    """
    anomaly_detection.py $mynorm
    """
}

process sex_inference {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'inferred_sex.json'
    label 'r'

    input:
    path imputed_mynorm_path
    val cpus
    path sample_sheet_path

    output:
    path "inferred_sex.json"

    script:
    """
    sex_inference.R $imputed_mynorm_path $cpus $sample_sheet_path
    """
}

process batch_effect {
    publishDir "$params.output", mode: 'copy', overwrite: true
    label 'python'

    input:
    path imputed_mynorm_path
    path sample_sheet_path
    each column

    output:
    path("Mean_beta_per_${column}/*.json", arity: "1..*")

    script:
    """
    batch_effect.py $imputed_mynorm_path $sample_sheet_path $column
    """
}

process beta_distribution {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: '*.json'
    label 'python'

    input:
    path imputed_mynorm_path
    val n_cpgs_beta_distr

    output:
    path "beta_distribution.json"

    script:
    """
    beta_distribution.py $imputed_mynorm_path $n_cpgs_beta_distr
    """
}

process nan_distribution {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: '*.json'
    label 'python'

    input:
    path qc_path
    path sample_sheet_path

    output:
    path "nan_distribution.json"

    script:
    """
    nan_distribution.py $qc_path $sample_sheet_path
    """
}

process pca {
    publishDir "$params.output", mode: 'copy', overwrite: true
    label 'python'

    input:
    path imputed_mynorm_path
    path sample_sheet_path
    val perc_pca_cpgs
    each column

    output:
    path "PCA_${column}.json"

    script:
    """
    pca.py $imputed_mynorm_path $sample_sheet_path $perc_pca_cpgs $column
    """
}