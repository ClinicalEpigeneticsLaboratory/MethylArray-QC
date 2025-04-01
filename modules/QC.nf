process QC {
    publishDir "${params.output}", mode: 'copy', overwrite: true, pattern: 'qc.parquet'
    label 'r_sesame'

    input:
    path idats
    val cpus
    path sample_sheet_path

    output:
    path "qc.parquet"

    script:
    """
    QC.R ${idats} ${cpus} ${sample_sheet_path}
    """
}
