process BETA_DISTRIBUTION {
    publishDir "${params.output}/Beta_distribution", mode: 'copy', overwrite: true, pattern: '*.json'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/Beta_distribution"    
    label 'python'

    input:
    path imputed_mynorm_path
    val n_rand_cpgs

    output:
    path "beta_distribution.json", emit: beta_distr_plot
    path "random_cpgs_to_plot.json", emit: n_rand_cpgs_path

    script:
    """
    beta_distribution.py ${imputed_mynorm_path} ${n_rand_cpgs}
    """
}
