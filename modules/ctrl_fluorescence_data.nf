process CTRL_FLUORESCENCE_DATA{
    publishDir "${params.output}/Control_probes_QC", mode: 'copy', overwrite: true
    label 'r_sesame'

    input:
    path idats
    path sample_sheet_path
    val cpus
    val metric

    output:
    path "ctrl_fluorescence.parquet", emit: ctrl_fluorescence_data_path
    path "ctrl_unique_probe_types.json", emit: ctrl_fluorescence_unique_probe_types

    script:
    """
    ctrl_fluorescence_data.R $idats $sample_sheet_path $cpus $metric
    """
}