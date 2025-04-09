process PCA {
    publishDir "${params.output}", mode: 'copy', overwrite: true
    label 'python'

    input:
    path imputed_mynorm_path
    path sample_sheet_path
    val perc_pca_cpgs
    val pca_number_of_components
    val pca_columns
    val pca_matrix_PC_count

    output:
    path "PCA_scatter_matrix_*.json", arity: "1..*", emit: scatter
    path "PCA_area.json", optional: true, emit: area
    path "PCA_PC_KW_test_*.json", arity: "1..*", emit: kruskal

    script:
    """
    pca.py ${imputed_mynorm_path} ${sample_sheet_path} ${perc_pca_cpgs} ${pca_number_of_components} ${pca_columns} ${pca_matrix_PC_count}
    """
}
