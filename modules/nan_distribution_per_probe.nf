process NAN_DISTRIBUTION_PER_PROBE {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: '*.json'
    label 'python'

    input:
    path raw_mynorm_path
    val nan_per_probe_n_cpgs

    output:
    path "nan_distribution_per_probe.json"

    script:
    """
    nan_distribution_per_probe.py $raw_mynorm_path $nan_per_probe_n_cpgs
    """
}