process ADDITIONAL_VALIDATORS_INIT {
    
    label 'python'
    
    input:
    path params_input
    path params_sample_sheet
    val params_cpus
    val params_pca_number_of_components
    val params_pca_matrix_PC_count

    script:
    """
    additional_validators_init.py $params_input $params_sample_sheet $params_cpus $params_pca_number_of_components $params_pca_matrix_PC_count
    """
}