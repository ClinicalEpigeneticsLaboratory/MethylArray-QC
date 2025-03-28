process pca {
    publishDir "$params.output", mode: 'copy', overwrite: true
    label 'python'

    input:
    path imputed_mynorm_path
    path sample_sheet_path
    val perc_pca_cpgs
    val pca_number_of_components
    each pca_param_pair // each pair consists of a column for 2D dotplot and a boolean (true/false) stating whether a scree plot will be drawn in this iteration
    val pca_matrix_PC_count

    output:
    //path "PCA_2D_dot_${pca_param_pair[0]}.json"
    path "PCA_scatter_matrix_${pca_param_pair[0]}.json"
    path "PCA_area.json", optional: true
    path "PCA_PC_KW_test_${pca_param_pair[0]}.json"

    script:
    """
    pca.py $imputed_mynorm_path $sample_sheet_path $perc_pca_cpgs $pca_number_of_components ${pca_param_pair[0]} ${pca_param_pair[1]} $pca_matrix_PC_count
    """
}