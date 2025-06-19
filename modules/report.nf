process REPORT {
    publishDir "${params.output}", mode: 'copy', overwrite: true, pattern: '*.html'
    label 'python'
    cache false

    input:
    //TODO: define all inputs for the report!!!
    path html_template
    path ao_plot_path
    path beta_distribution_plot
    path nan_distribution_per_probe_plot
    path nan_distribution_per_sample_plot
    val batch_effect_plot_paths
    path sex_inference_path
    path params_path

    output:
    path "qc_report.html"

    script:
    """
    report.py ${html_template} ${ao_plot_path} ${beta_distribution_plot} ${nan_distribution_per_probe_plot} ${nan_distribution_per_sample_plot} ${batch_effect_plot_paths} ${sex_inference_path} ${params_path}
    """
}
