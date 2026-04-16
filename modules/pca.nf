process PCA {
    publishDir "${params.output}/PCA/Scatter_matrix", mode: 'copy', overwrite: true, pattern: 'PCA_scatter_matrix_*.json'
    publishDir "${params.output}/PCA", mode: 'copy', overwrite: true, pattern: 'PCA_area_plot.json'
    publishDir "${params.output}/PCA/Kruskal", mode: 'copy', overwrite: true, pattern: 'PCA_PC_KW_test_*.json'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/PCA/Scatter_matrix ${params.output}/PCA/Kruskal"
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
    path "PCA_area_plot.json", optional: true, emit: area
    path "PCA_PC_KW_test_*.json", arity: "1..*", emit: kruskal

    script:
    """
    pca.py ${imputed_mynorm_path} ${sample_sheet_path} ${perc_pca_cpgs} ${pca_number_of_components} ${pca_columns} ${pca_matrix_PC_count}
    """

    stub:
    """
    touch PCA_scatter_matrix_stub.json
    touch PCA_area_plot.json
    touch PCA_PC_KW_test_stub.json
    """
}
