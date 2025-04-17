process NAN_DISTRIBUTION_PER_SAMPLE {
    publishDir "${params.output}/NaN_distribution", mode: 'copy', overwrite: true, pattern: '*.json'
    label 'python'

    input:
    path qc_path
    path sample_sheet_path

    output:
    path "nan_distribution_per_sample.json"

    script:
    """
    nan_distribution_per_sample.py ${qc_path} ${sample_sheet_path}
    """
}
