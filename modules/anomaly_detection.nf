process ANOMALY_DETECTION {
    publishDir "${params.output}/Anomaly_detection", mode: 'copy', overwrite: true, pattern: 'ao_*'
    label 'python'

    input:
    path mynorm
    val contamination

    output:
    path "ao_results.parquet", emit: ao_results
    path "ao_plot.json", emit: ao_plot

    script:
    """
    anomaly_detection.py ${mynorm} ${contamination}
    """
}
