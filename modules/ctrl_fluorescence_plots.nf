process CTRL_FLUORESCENCE_PLOTS {
    publishDir "${params.output}/Control_probes_QC/Plots/${ctrl_probe_type}", mode: 'copy', overwrite: true, pattern: '*_by_*.json'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/Control_probes_QC/Plots/${ctrl_probe_type}"
    label 'python'

    input:
    path path_to_ctrl_fluorescence_data
    path path_to_sample_sheet
    each column
    each ctrl_probe_type

    output:
    path "${ctrl_probe_type}_by_${column}.json", arity: "1..*"

    script:
    """
    ctrl_fluorescence_plots.py ${path_to_ctrl_fluorescence_data} ${path_to_sample_sheet} ${column} ${ctrl_probe_type}
    """
}