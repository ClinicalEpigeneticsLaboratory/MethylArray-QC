process SEX_INFERENCE {
    publishDir "${params.output}/Sex_inference", mode: 'copy', overwrite: true, pattern: 'inferred_sex.json'
    label 'r_sesame'

    input:
    path imputed_mynorm_path
    val cpus
    path sample_sheet_path

    output:
    path "inferred_sex.json"

    script:
    """
    sex_inference.R ${imputed_mynorm_path} ${cpus} ${sample_sheet_path}
    """
}
