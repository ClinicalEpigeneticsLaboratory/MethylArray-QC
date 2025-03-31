include { validateParameters; paramsSummaryLog; paramsHelp; paramsSummaryMap; samplesheetToList} from 'plugin/nf-schema'
include { QC } from './modules/QC.nf'
include { PREPROCESS } from './modules/preprocess.nf'
include { IMPUTE } from './modules/impute.nf'
include { ANOMALY_DETECTION } from './modules/anomaly_detection.nf'
include { SEX_INFERENCE } from './modules/sex_inference.nf'
include { BATCH_EFFECT } from './modules/batch_effect.nf'
include { BETA_DISTRIBUTION } from './modules/beta_distribution.nf'
include { NAN_DISTRIBUTION_PER_SAMPLE } from './modules/nan_distribution_per_sample.nf'
include { NAN_DISTRIBUTION_PER_PROBE } from './modules/nan_distribution_per_probe.nf'
include { PCA } from './modules/pca.nf'

//Default values for parameters stored in nextflow.config (ref. https://www.nextflow.io/docs/latest/cli.html#cli-params)

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

    raw_mynorm = PREPROCESS(params.input, params.cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method, params.sample_sheet)
    (imputed_mynorm, nan_per_sample, nan_per_probe) = IMPUTE(raw_mynorm, params.p_threshold, params.s_threshold, params.imputer_type)

    ANOMALY_DETECTION(imputed_mynorm)

    // run sex_inference process when parameter infer_sex is set to true
    if(params.infer_sex) {
        SEX_INFERENCE(imputed_mynorm, params.cpus, params.sample_sheet)
    }

    BATCH_EFFECT(imputed_mynorm, params.sample_sheet, ["Sentrix_ID", "Sentrix_Position"])

    BETA_DISTRIBUTION(imputed_mynorm, params.n_cpgs_beta_distr)
    NAN_DISTRIBUTION_PER_SAMPLE(qc_path, params.sample_sheet)
    NAN_DISTRIBUTION_PER_PROBE(raw_mynorm, params.top_nan_per_probe_cpgs)

    def pca_columns = params.pca_columns?.split(',') as List

    // draw_area passed together with column ensures that area plot for PCA cumulative variance will be drawn only once - for the first execution of a PCA process
    def draw_area = pca_columns.collect{it -> it == pca_columns.getAt(0)}

    def pca_param_ch = Channel.fromList(pca_columns)
        .merge(Channel.fromList(draw_area))

    PCA(imputed_mynorm, params.sample_sheet, params.perc_pca_cpgs, params.pca_number_of_components, pca_param_ch, params.pca_matrix_PC_count)

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
