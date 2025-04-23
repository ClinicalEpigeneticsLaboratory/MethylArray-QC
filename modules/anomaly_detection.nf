process ANOMALY_DETECTION {
    publishDir "${params.output}/Anomaly_detection", mode: 'copy', overwrite: true, pattern: 'ao_*'
    label 'python'

    input:
    path mynorm
    val contamination

    output:
    path "ao_results.parquet"
    path "ao_plot.json"

    script:
    """
    anomaly_detection.py ${mynorm} ${contamination}
    """
}
