process EPIGENETIC_AGE_INFERENCE{
    publishDir "${params.output}/Epi_age", mode: 'copy', overwrite: true
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/Epi_age"
    label 'r_clock'

    input:
    path sample_sheet_path
    path imputed_mynorm_path
    val epi_clocks

    output:
    path "epi_clocks_res.parquet", emit: epi_clocks_res_parquet
    path "epi_clocks_res.json", emit: epi_clocks_res_json

    script:
    """
    epigenetic_age_inference.R $sample_sheet_path $imputed_mynorm_path $epi_clocks
    """

    stub:
    """
    touch epi_clocks_res.parquet
    touch epi_clocks_res.json
    """
}