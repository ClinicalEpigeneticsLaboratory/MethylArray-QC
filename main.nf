include { validateParameters; paramsSummaryLog; paramsHelp; paramsSummaryMap; samplesheetToList} from 'plugin/nf-schema'
include { QC; preprocess; impute; anomaly_detection; sex_inference; batch_effect; beta_distribution; nan_distribution; pca } from './modules.nf'
workflow {
    validateParameters()

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

    qc_path = QC(params.input, params.cpus, params.sample_sheet)

    raw_mynorm = preprocess(params.input, params.cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method, params.sample_sheet)
    imputed_mynorm = impute(raw_mynorm, params.p_threshold, params.s_threshold, params.imputer_type)
    // TODO: export stats from imputation as JSON file (%NaN per sample/per CpG)...

    anomaly_detection(imputed_mynorm)

    // run sex_inference process when parameter infer_sex is set to true
    if(params.infer_sex) {
        sex_inference(imputed_mynorm, params.cpus, params.sample_sheet)
    }

    batch_effect(imputed_mynorm, params.sample_sheet, ["Sentrix_ID", "Sentrix_Position"])

    if(params.n_cpgs_beta_distr) {
        beta_distribution(imputed_mynorm, params.n_cpgs_beta_distr)
    } else {
        beta_distribution(imputed_mynorm, 10000)
    }
    
    nan_distribution(qc_path, params.sample_sheet)

    def perc_pca_cpgs = 10
    if(params.perc_pca_cpgs) {
        perc_pca_cpgs = params.perc_pca_cpgs
    } 

    def pca_number_of_components = 10
    if(params.pca_number_of_components) {
        pca_number_of_components = params.pca_number_of_components
    } 

    def pca_columns = ['Sentrix_ID', 'Sentrix_Position']
    if(params.pca_columns) {
        pca_columns = params.pca_columns?.split(',') as List
    }

    // ensures that scree plot for PCA will be drawn only once - for the first execution of a PCA process
    def draw_scree = pca_columns.collect{it -> it == pca_columns.getAt(0)}

    def pca_param_ch = Channel.fromList(pca_columns)
        .merge(Channel.fromList(draw_scree))

    pca(imputed_mynorm, params.sample_sheet, perc_pca_cpgs, pca_number_of_components, pca_param_ch)

    // TODO: (1) NaN distribution across probes (heatmap), samples (TODO: add parameter for a number of samples per plot)
    // (2) multiprocessing for analyses where possible

    /* 
    Moved saving params to the end of the workflow to add parameters such as workflow duration etc.
    
    Temporary manual parameter map flattening - some of the options had to be removed as JSON conversion returned weird StackOverflow error when there were too many items in a map despite map flattening
    Structure flattening neccessary because of unresolved Nextflow bug: https://github.com/nextflow-io/nextflow/issues/2815
    
    Assignment of a handler neccessary due to unresolved Nextflow bug: https://github.com/nextflow-io/nextflow/issues/5261
    https://github.com/nextflow-io/nextflow/issues/5445
    */
    workflow.onComplete = {
        def params_map_all = paramsSummaryMap(workflow)
        def paramExporter = new JsonWorkflowParamExporter()
        file("${params.output}/params.json").text = paramExporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size)
        println("Workflow completed")
    }

    workflow.onError = {
        def params_map_all = paramsSummaryMap(workflow)
        def paramExporter = new JsonWorkflowParamExporter()
        file("${params.output}/params.json").text = paramExporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size)
        println("Workflow completed with errors")
    }
}

/*
Left here for now due to sometimes appearing error (unknown cause): 
Variable `workflow` already defined in the process scope
when this declaration is within workflow scope
*/
log.info paramsSummaryLog(workflow)
