process ANOMALY_DETECTION {
    publishDir "${params.output}/Anomaly_detection", mode: 'copy', overwrite: true, pattern: 'ao_*'
    // added a beforeScript directive due to WSL-Windows integration issues
    beforeScript "mkdir -p ${params.output}/Anomaly_detection"
    label 'python'

    input:
    path mynorm
    val contamination
    val language

    output:
    path "ao_results.parquet", emit: ao_results
    path "ao_plot.json", emit: ao_plot

    script:
    """
    anomaly_detection.py ${mynorm} ${contamination} ${language}
    """

    stub:
    """
    touch ao_results.parquet
    touch ao_plot.json
    """
}
