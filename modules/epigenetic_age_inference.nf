process EPIGENETIC_AGE_INFERENCE{
    publishDir "${params.output}/Epi_age", mode: 'copy', overwrite: true
    label 'r_clock'

    input:
    path sample_sheet_path
    path imputed_mynorm_path
    val epi_clocks

    output:
    path "epi_clocks_res.parquet"

    script:
    """
    epigenetic_age_inference.R $sample_sheet_path $imputed_mynorm_path $epi_clocks
    """
}