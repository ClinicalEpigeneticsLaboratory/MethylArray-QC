include { validateParameters; paramsSummaryLog } from 'plugin/nf-schema'

// General
//params.input = "/mnt/c/Users/jan.binkowski/Desktop/test/idats"
//params.output = "/mnt/c/Users/jan.binkowski/Desktop/test/output"
//params.cpus = 10

// Sesame
//params.prep_code = "QCDPB"
//params.collapse_prefix = "TRUE"
//params.collapse_prefix_method = "mean"

// Imputation
//params.p_threshold = 0.2
//params.s_threshold = 0.2
//params.imputer_type = "knn"



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

process impute {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'imputed_mynorm.parquet'
    label 'python'

    input:
    path mynorm
    val p_threshold
    val s_threshold
    val imputer_type

    output:
    path "imputed_mynorm.parquet"

    script:
    """
    imputation.py $mynorm $p_threshold $s_threshold $imputer_type
    """
}

process anomaly_detection {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'ao_results.parquet'
    label 'python'

    input:
    path mynorm

    output:
    path "ao_results.parquet"

    script:
    """
    anomaly_detection.py $mynorm
    """
}

workflow {
    validateParameters()
    idats = file("${params.input}", checkIfExists: true, checkIfEmpty: true)

    idat_list_size = file("$idats/{*.idat,*.idat.gz}").size()
    sample_size = idat_list_size/2

    // TODO: try to rewrite this if-else to assertions (they do not work yet)!
    // TODO: sample sheet validation (sample sheet schema?) and comparison with IDAT list 
    // Current sample count validation based ONLY on the number of IDAT files!
    if(idat_list_size == 0) {
        error "Input directory does not contain IDAT files!"
    } else {
        if(idat_list_size % 2 != 0) {
            error "Number of IDAT files is not a multiplication of 2 and there should be 2 IDATs per one sample - did you forget to copy some files?"
        }
    }

    //assert idat_list_size == 0 : "Input directory does not contain IDAT files!"
    //assert idat_list_size != 0 & idat_list_size % 2 != 0 : "Number of IDAT files is not a multiplication of 2 - did you forget to copy a file?"
    println "\nYou provided $idat_list_size IDAT files ($sample_size samples)"

    // TODO: add internal validation, count files, check sample sheet etc.
    QC(idats, params.cpus)

    raw_mynorm = preprocess(idats, params.cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method)
    imputed_mynorm = impute(raw_mynorm, params.p_threshold, params.s_threshold, params.imputer_type)
    // TODO: export stats from imputation as JSON file ...

    anomaly_detection(imputed_mynorm)
    // TODO: (1) PCA (2) Beta distribution across slides/arrays/groups (3) NaN distribution across slides/arrays/groups
    // (4) multiprocessing for
}

log.info paramsSummaryLog(workflow)