params.input = "/mnt/c/Users/jan.binkowski/Desktop/test/idats"
params.output = "/mnt/c/Users/jan.binkowski/Desktop/test/output"
params.cpus = 10
params.prep_code = "QCDPB"
params.collapse_prefix = "TRUE"
params.collapse_prefix_method = "mean"

process QC {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'qc.parquet'
    label 'r'

    input:
    path idats
    val cpus

    output:
    path "qc.parquet"

    script:
    """
    QC.R $idats $cpus
    """
}

process preprocess {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'raw_mynorm.parquet'
    label 'r'

    input:
    path idats
    val cpus
    val prep_code
    val collapse_prefix
    val collapse_prefix_method

    output:
    path "raw_mynorm.parquet"

    script:
    """
    preprocess.R $idats $cpus $prep_code $collapse_prefix $collapse_prefix_method
    """

}

workflow {
    idats = file("${params.input}", checkIfExists: true)
    // add internal validation, count files, check sample sheet etc.
    QC(idats, params.cpus)
    preprocess(idats, params.cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method)
}