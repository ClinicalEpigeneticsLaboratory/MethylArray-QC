process REPORT {
    publishDir "${params.output}", mode: 'copy', overwrite: true, pattern: '*.html'
    label 'python'
    cache false

    input:
    path html_template
    path qc_summary_path
    val ctrl_fluorescence_plot_paths
    path preprocess_summary_path
    path imputation_summary_path
    path ao_plot_path
    path beta_distribution_plot
    path nan_distribution_per_probe_plot
    path nan_distribution_per_sample_plot
    val batch_effect_plot_paths
    path sex_inference_path
    path params_path
    val pca_kruskal_paths
    val pca_plot_paths
    val epi_age_paths
    val unique_probe_types_str

    output:
    path "qc_report.html"

    script:
    """
    report.py ${html_template} ${qc_summary_path} ${ctrl_fluorescence_plot_paths} ${preprocess_summary_path} ${imputation_summary_path} ${ao_plot_path} ${beta_distribution_plot} ${nan_distribution_per_probe_plot} ${nan_distribution_per_sample_plot} ${batch_effect_plot_paths} ${sex_inference_path} ${params_path} ${pca_kruskal_paths} ${pca_plot_paths} ${epi_age_paths} ${unique_probe_types_str}
    """
}
