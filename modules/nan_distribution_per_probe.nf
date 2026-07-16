process NAN_DISTRIBUTION_PER_PROBE {
    publishDir "$params.output/NaN_distribution", mode: 'copy', overwrite: true, pattern: '*.json'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p $params.output/NaN_distribution"
    label 'python'

    input:
    path raw_mynorm_path
    val nan_per_probe_n_cpgs
    val language

    output:
    path "nan_distribution_per_probe.json"

    script:
    """
    nan_distribution_per_probe.py $raw_mynorm_path $nan_per_probe_n_cpgs $language
    """

    stub:
    """
    touch nan_distribution_per_probe.json
    """
}