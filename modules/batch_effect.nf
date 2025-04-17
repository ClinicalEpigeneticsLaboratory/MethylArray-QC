process BATCH_EFFECT {
    publishDir "${params.output}/Batch_effect/Mean_beta_per_${column}", mode: 'copy', overwrite: true
    label 'python'

    input:
    path imputed_mynorm_path
    path sample_sheet_path
    each column

    output:
    path "*.json", arity: "1..*"

    script:
    """
    batch_effect.py ${imputed_mynorm_path} ${sample_sheet_path} ${column}
    """
}
