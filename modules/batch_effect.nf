process BATCH_EFFECT {

    publishDir "${params.output}/Batch_effect/Mean_beta_per_${column}", mode: 'copy', overwrite: true
    
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/Batch_effect/Mean_beta_per_${column}"

    label 'python'
        
    debug true

    input:
    path imputed_mynorm_path
    path sample_sheet_path
    each column
    path n_rand_cpgs_path

    output:
    path "${column}_*.json", arity: "1..*"

    script:
    """
    batch_effect.py ${imputed_mynorm_path} ${sample_sheet_path} ${column} ${n_rand_cpgs_path}
    """
}
