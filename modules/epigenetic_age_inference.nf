process EPIGENETIC_AGE_INFERENCE{
    publishDir "${params.output}", mode: 'copy', overwrite: true
    label 'r_other'

    input:
    path sample_sheet_path
    path imputed_mynorm_path
    val epi_clocks

    output:
    path "epi_clocks_res.csv"

    script:
    """
    epigenetic_age_inference.R $sample_sheet_path $imputed_mynorm_path $epi_clocks
    """
}