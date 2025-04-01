process PREPROCESS {
    publishDir "${params.output}", mode: 'copy', overwrite: true, pattern: 'raw_mynorm.parquet'
    label 'r_sesame'

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
    preprocess.R ${idats} ${cpus} ${prep_code} ${collapse_prefix} ${collapse_prefix_method} ${sample_sheet_path}
    """
}
