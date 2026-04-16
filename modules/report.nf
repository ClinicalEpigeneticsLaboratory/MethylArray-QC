// TODO: MEMORY PROBLEM!!! 
process REPORT {
    publishDir "${params.output}", mode: 'copy', overwrite: true, pattern: '*.html'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p $params.output"
    label 'python'
    cache false
    memory { 4.GB * task.attempt }
    errorStrategy { task.exitStatus in 137..140 ? 'retry' : 'terminate' }
    maxRetries 3
    //debug true

    input:
    path html_template
    path qc_summary_path,                  stageAs: 'qc_summary.json'
    val  ctrl_fluorescence_plot_paths
    path preprocess_summary_path,          stageAs: 'preprocess_summary.json'
    path imputation_summary_path,          stageAs: 'imputation_summary.json'
    path ao_plot_path,                     stageAs: 'ao_plot.txt'
    path beta_distribution_plot,           stageAs: 'beta_distribution.txt'
    path nan_distribution_per_probe_plot,  stageAs: 'nan_per_probe.txt'
    path nan_distribution_per_sample_plot, stageAs: 'nan_per_sample.txt'
    val  batch_effect_plot_paths
    path sex_inference_path,               stageAs: 'sex_inference.json'
    path params_path,                      stageAs: 'params.json'
    val  pca_kruskal_paths
    val  pca_plot_paths
    val  epi_age_paths
    val  unique_probe_types_str

    output:
    path "qc_report.html"

    script:
    """
    report.py ${html_template} ${qc_summary_path} ${ctrl_fluorescence_plot_paths} ${preprocess_summary_path} ${imputation_summary_path} ${ao_plot_path} ${beta_distribution_plot} ${nan_distribution_per_probe_plot} ${nan_distribution_per_sample_plot} ${batch_effect_plot_paths} ${sex_inference_path} ${params_path} ${pca_kruskal_paths} ${pca_plot_paths} ${epi_age_paths} ${unique_probe_types_str}
    """

    stub:
    """
    touch qc_report.html
    """
}
