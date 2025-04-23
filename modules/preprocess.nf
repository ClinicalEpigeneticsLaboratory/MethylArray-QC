process PREPROCESS {
    publishDir "${params.output}/Preprocess", mode: 'copy', overwrite: true, pattern: "raw_mynorm*"
    label 'r_sesame'

    input:
    path idats
    val cpus
    val prep_code
    val collapse_prefix
    val collapse_prefix_method
    path sample_sheet_path

    output:
    path "raw_mynorm.parquet", emit: raw_mynorm_path
    path "raw_mynorm_probe_count.json", emit: raw_mynorm_probe_count_path

    script:
    """
    preprocess.R ${idats} ${cpus} ${prep_code} ${collapse_prefix} ${collapse_prefix_method} ${sample_sheet_path}
    """
}
