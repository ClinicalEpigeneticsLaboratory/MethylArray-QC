process NAN_DISTRIBUTION_PER_SAMPLE {
    publishDir "${params.output}/NaN_distribution", mode: 'copy', overwrite: true, pattern: '*.json'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p $params.output/NaN_distribution"
    label 'python'

    input:
    path qc_path
    path sample_sheet_path

    output:
    path "nan_distribution_per_sample_*.json", arity: "1..*"

    script:
    """
    nan_distribution_per_sample.py ${qc_path} ${sample_sheet_path}
    """

    stub:
    """
    touch nan_distribution_per_sample_stub.json
    """
}
