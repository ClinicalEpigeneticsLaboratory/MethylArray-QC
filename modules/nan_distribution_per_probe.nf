process nan_distribution_per_probe {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: '*.json'
    label 'python'

    input:
    path raw_mynorm_path
    val top_nan_per_probe_cpgs

    output:
    path "nan_distribution_per_probe.json"

    script:
    """
    nan_distribution_per_probe.py $raw_mynorm_path $top_nan_per_probe_cpgs
    """
}