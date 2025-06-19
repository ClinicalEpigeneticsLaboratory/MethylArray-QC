process QC {
    publishDir "${params.output}/QC", mode: 'copy', overwrite: true, pattern: 'qc*'
    label 'r_sesame'

    input:
    path idats
    val cpus
    path sample_sheet_path

    output:
    path "qc.parquet", emit: qc_parquet
    path "qc.json", emit: qc_json

    script:
    """
    QC.R ${idats} ${cpus} ${sample_sheet_path}
    """
}
