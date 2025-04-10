process BETA_DISTRIBUTION {
    publishDir "${params.output}", mode: 'copy', overwrite: true, pattern: '*.json'
    label 'python'

    input:
    path imputed_mynorm_path
    val n_cpgs_beta_distr

    output:
    path "beta_distribution.json"

    script:
    """
    beta_distribution.py ${imputed_mynorm_path} ${n_cpgs_beta_distr}
    """
}
