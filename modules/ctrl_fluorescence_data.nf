process CTRL_FLUORESCENCE_DATA{
    publishDir "${params.output}/Control_probes_QC", mode: 'copy', overwrite: true
    label 'r_sesame'

    input:
    path idats
    path sample_sheet_path
    val cpus

    output:
    path "ctrl_fluorescence.parquet"

    script:
    """
    ctrl_fluorescence_data.R $idats $sample_sheet_path $cpus
    """
}