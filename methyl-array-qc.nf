include { validateParameters; paramsSummaryLog; paramsHelp; paramsSummaryMap; samplesheetToList} from 'plugin/nf-schema'

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

process saveParams {

    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'params.json'
    label 'r'

    output:
        path 'params.json', emit: json

    script:

    /* TODO: export: 
     - number of IDAT files, 
     - version (Nextflow? Python? R? MethylArray-QC version?), 
     - when the workflow was started/completed (date + time), 
     - workflow duration
     - whether the workflow succeeded
    */
    json_params = groovy.json.JsonOutput.toJson(params)
    pretty_json = groovy.json.JsonOutput.prettyPrint(json_params)
    "echo '${pretty_json}' > params.json"
}

process QC {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'qc.parquet'
    label 'r'

    input:
    path idats
    val cpus
    path sample_sheet_path

    output:
    path "qc.parquet"

    script:
    """
    QC.R $idats $cpus $sample_sheet_path
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
    path sample_sheet_path

    output:
    path "raw_mynorm.parquet"

    script:
    """
    preprocess.R $idats $cpus $prep_code $collapse_prefix $collapse_prefix_method $sample_sheet_path
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

process sex_inference {
    publishDir "$params.output", mode: 'copy', overwrite: true, pattern: 'inferred_sex.json'
    label 'r'

    input:
    path imputed_mynorm_path
    val cpus
    path sample_sheet_path

    output:
    path "inferred_sex.json"

    script:
    """
    sex_inference.R $imputed_mynorm_path $cpus $sample_sheet_path
    """
}

workflow {
    validateParameters()
    saveParams()

    // Parameter validation left if-based: explanation - https://stackoverflow.com/questions/13832487/why-should-assertions-not-be-used-for-argument-checking-in-public-methods
    
    idats = file("${params.input}", checkIfExists: true, checkIfEmpty: true)

    idat_list_size = file("$idats/{*.idat,*.idat.gz}").size()

    if(idat_list_size == 0) {
        error "Input directory does not contain IDAT files!"
    } else {
        if(idat_list_size % 2 != 0) {
            error "Number of IDAT files is not a multiplication of 2 and there should be 2 IDATs per one sample - did you forget to copy some files?"
        }
    }

    QC(params.input, params.cpus, params.sample_sheet)

    raw_mynorm = preprocess(params.input, params.cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method, params.sample_sheet)
    imputed_mynorm = impute(raw_mynorm, params.p_threshold, params.s_threshold, params.imputer_type)
    // TODO: export stats from imputation as JSON file ...

    anomaly_detection(imputed_mynorm)

    // run sex_inference process in parameter infer_sex is set to true
    if(params.infer_sex) {
        sex_inference(imputed_mynorm, params.cpus, params.sample_sheet)
    }
   
    // TODO: (1) PCA (2) Beta distribution across slides/arrays/groups (3) NaN distribution across slides/arrays/groups
    // (4) multiprocessing for
}

log.info paramsSummaryLog(workflow)