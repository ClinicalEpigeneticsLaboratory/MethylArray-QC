process ADDITIONAL_VALIDATORS_AFTER_IMPUTE {
    
    label 'python'
    
    input:
    val params_n_cpgs_beta_distr
    val params_nan_per_probe_n_cpgs
    path imputed_mynorm_n_cpgs_path

    script:
    """
    additional_validators_after_impute.py $params_n_cpgs_beta_distr $params_nan_per_probe_n_cpgs $imputed_mynorm_n_cpgs_path
    """
}