include { validateParameters; paramsSummaryLog; paramsSummaryMap } from 'plugin/nf-schema'
include { ADDITIONAL_VALIDATORS_INIT } from './modules/additional_validators_init.nf'
include { QC } from './modules/QC.nf'
include { CTRL_FLUORESCENCE_DATA } from './modules/ctrl_fluorescence_data.nf'
include { PREPROCESS } from './modules/preprocess.nf'
include { IMPUTE } from './modules/impute.nf'
include { ADDITIONAL_VALIDATORS_AFTER_IMPUTE } from './modules/additional_validators_after_impute.nf'
include { ANOMALY_DETECTION } from './modules/anomaly_detection.nf'
include { SEX_INFERENCE } from './modules/sex_inference.nf'
include { BATCH_EFFECT } from './modules/batch_effect.nf'
include { BETA_DISTRIBUTION } from './modules/beta_distribution.nf'
include { NAN_DISTRIBUTION_PER_SAMPLE } from './modules/nan_distribution_per_sample.nf'
include { NAN_DISTRIBUTION_PER_PROBE } from './modules/nan_distribution_per_probe.nf'
include { PCA } from './modules/pca.nf'
include { EPIGENETIC_AGE_INFERENCE } from './modules/epigenetic_age_inference.nf'
include { EPIGENETIC_AGE_PLOTS } from './modules/epigenetic_age_plots.nf'
include { CTRL_FLUORESCENCE_PLOTS } from './modules/ctrl_fluorescence_plots.nf'
include { REPORT } from './modules/report.nf'

//Default values for parameters stored in nextflow.config (ref. https://www.nextflow.io/docs/latest/cli.html#cli-params)

workflow {

    validateParameters()

    def input_abs_path = file(params.input).toAbsolutePath()
    def sample_sheet_abs_path = file(params.sample_sheet).toAbsolutePath()

    ADDITIONAL_VALIDATORS_INIT(input_abs_path, sample_sheet_abs_path, params.cpus, params.pca_number_of_components, params.pca_matrix_PC_count)

    def cpus = params.cpus
    if(params.cpus == -1) {
        cpus = Runtime.runtime.availableProcessors() - 1
        println("cpus parameter set to -1 - ${cpus} CPUs will be used")
    }

    def processed_samples_count = file("$sample_sheet_abs_path").countLines()-1

    qc_path = QC(input_abs_path, cpus, sample_sheet_abs_path)
    
    if(params.ctrl_intens_plots) {
        // ctrl_fluorescence_data_ch_out.ctrl_fluorescence_data_path: control probe fluorescence data file path
        // ctrl_fluorescence_data_ch_out.ctrl_fluorescence_unique_probe_types: unique control probe types JSON file path
        ctrl_fluorescence_data_ch_out = CTRL_FLUORESCENCE_DATA(input_abs_path, sample_sheet_abs_path, cpus, params.ctrl_intens_metric)

        def unique_grouping_cols = params.ctrl_intens_cols?.split(',') as List

        def unique_probe_types = ctrl_fluorescence_data_ch_out.ctrl_fluorescence_unique_probe_types.map { jsonFilePath ->
            try {
                def jsonText = file(jsonFilePath).text
                def typesList = new groovy.json.JsonSlurper().parseText(jsonText)
                if (typesList instanceof String) {
                    typesList = typesList.split(',') as List
                }
                return typesList
            } catch (Exception e) {
                println "Failed to parse JSON from $jsonFilePath : $e"
                return []  // or handle error as needed
            }
        }

        // Now you can use 'unique_types_ch' as a channel of lists
        unique_probe_types.subscribe { list ->
            println "Unique types from JSON: $list"
        }

        ctrl_fluorescence_plots_ch_out = CTRL_FLUORESCENCE_PLOTS(ctrl_fluorescence_data_ch_out.ctrl_fluorescence_data_path, sample_sheet_abs_path, unique_grouping_cols, unique_probe_types)
    }

    // preprocess_ch_out.raw_mynorm_path: imputed mynorm path
    // preprocess_ch_out.raw_mynorm_probe_count_path: raw mynorm probe count JSON file path
    preprocess_ch_out = PREPROCESS(input_abs_path, cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method, sample_sheet_abs_path)
    
    // impute_ch_out.imputed_mynorm: imputed mynorm path
    // impute_ch_out.nan_per_sample: path to file with %NaN per sample stats
    // impute_ch_out.nan_per_probe: path to file with %NaN per probe stats
    // impute_ch_out.mynorm_imputed_n_cpgs: number of CpGs in imputed mynorm
    impute_ch_out = IMPUTE(preprocess_ch_out.raw_mynorm_path, params.p_threshold, params.s_threshold, params.imputer_type)

    if(impute_ch_out) {
        ADDITIONAL_VALIDATORS_AFTER_IMPUTE(params.n_cpgs_beta_distr, params.nan_per_probe_n_cpgs, impute_ch_out.mynorm_imputed_n_cpgs)
    }

    if(processed_samples_count > 2) {
        ao_results = ANOMALY_DETECTION(impute_ch_out.imputed_mynorm, params.contamination)
        ao_plot_path = ao_results.ao_plot
    } else {
        ao_plot_path = "$projectDir/assets/NO_FILE.txt"
    }

    // run sex_inference process when parameter infer_sex is set to true
    if(params.infer_sex) {
        sex_inference_path = SEX_INFERENCE(impute_ch_out.imputed_mynorm, cpus, sample_sheet_abs_path)
    }

    batch_effect_ch_out = BATCH_EFFECT(impute_ch_out.imputed_mynorm, sample_sheet_abs_path, ["Sentrix_ID", "Sentrix_Position"])

    // batch_effect_ch_out.sentrix_id: paths to batch effect evaluation boxplots for Sentrix IDs
    // batch_effect_ch_out.sentrix_position: path to batch effect evaluation boxplots for Sentrix Position
    batch_effect_ch_out
        .branch { path -> 
                    sentrix_id:
                        path =~ /Sentrix_ID/
                    sentrix_position:
                        path =~ /Sentrix_Position/
        }
        .set{batch_effect_ch_out}

    batch_effect_plot_paths = batch_effect_ch_out.sentrix_id
        .merge(batch_effect_ch_out.sentrix_position)
        .collect()
        .map {
            it.join(',')
        }

    beta_distr_plot = BETA_DISTRIBUTION(impute_ch_out.imputed_mynorm, params.n_cpgs_beta_distr)
    nan_per_sample_plot = NAN_DISTRIBUTION_PER_SAMPLE(qc_path, sample_sheet_abs_path)
    nan_per_probe_plot = NAN_DISTRIBUTION_PER_PROBE(preprocess_ch_out.raw_mynorm_path, params.nan_per_probe_n_cpgs)

    // pca_ch_out.area: area plot path
    // pca_ch_out.scatter: scatter matrix plot paths
    // pca_ch_out.kruskal: Kruskal-Wallis test results
    pca_ch_out = PCA(impute_ch_out.imputed_mynorm, sample_sheet_abs_path, params.perc_pca_cpgs, params.pca_number_of_components, params.pca_columns, params.pca_matrix_PC_count)

    if(params.infer_epi_age) {
        epi_age_res_path = EPIGENETIC_AGE_INFERENCE(sample_sheet_abs_path, impute_ch_out.imputed_mynorm, params.epi_clocks)
        epi_age_plots_ch_out = EPIGENETIC_AGE_PLOTS(epi_age_res_path, sample_sheet_abs_path, params.epi_clocks?.split(',') as List)
    }

    report_template_path = file("${projectDir}/templates/report.html", checkIfExists: true)
    params_path = file("${params.output}/params.json")

    REPORT(
        report_template_path,
        ao_plot_path,
        beta_distr_plot,
        nan_per_probe_plot,
        nan_per_sample_plot,
        batch_effect_plot_paths,
        params_path
    )

    /* 
    Moved saving params to the end of the workflow to add parameters such as workflow duration etc.
    
    Temporary manual parameter map flattening - some of the options had to be removed as JSON conversion returned weird StackOverflow error when there were too many items in a map despite map flattening
    Structure flattening neccessary because of unresolved Nextflow bug: https://github.com/nextflow-io/nextflow/issues/2815
    
    Assignment of a handler neccessary due to unresolved Nextflow bug: https://github.com/nextflow-io/nextflow/issues/5261
    https://github.com/nextflow-io/nextflow/issues/5445
    */
    workflow.onComplete = {
        def params_map_all = paramsSummaryMap(workflow)
        def idat_list_size = file("$input_abs_path/{*.idat,*.idat.gz}").size()
        def paramExporter = new JsonWorkflowParamExporter()
        file("${params.output}/params.json").text = paramExporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size, processed_samples_count, impute_ch_out.mynorm_imputed_n_cpgs.val.toString(), preprocess_ch_out.raw_mynorm_probe_count_path.val.toString())
        println("Workflow completed")
    }

    workflow.onError = {
        def params_map_all = paramsSummaryMap(workflow)
        def idat_list_size = file("$input_abs_path/{*.idat,*.idat.gz}").size()
        def paramExporter = new JsonWorkflowParamExporter()
        file("${params.output}/params.json").text = paramExporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size, processed_samples_count, impute_ch_out.mynorm_imputed_n_cpgs.val.toString(), preprocess_ch_out.raw_mynorm_probe_count_path.val.toString())
        println("Workflow completed with errors")
    }
}

/*
Left here for now due to sometimes appearing error (unknown cause): 
Variable `workflow` already defined in the process scope
when this declaration is within workflow scope
*/
log.info paramsSummaryLog(workflow)
