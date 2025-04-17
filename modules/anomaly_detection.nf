process ANOMALY_DETECTION {
    publishDir "${params.output}/Anomaly_detection", mode: 'copy', overwrite: true, pattern: 'ao_results.parquet'
    label 'python'

    input:
    path mynorm
    val contamination

    output:
    path "ao_results.parquet"

    script:
    """
    anomaly_detection.py ${mynorm} ${contamination}
    """
}
