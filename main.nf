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

    def workflow_start = java.time.Instant.now()

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

    // qc_ch_out.qc_parquet: QC stats exported as PARQUET
    // qc_ch_out.qc_json: QC stats exported as JSON
    qc_ch_out = QC(input_abs_path, cpus, sample_sheet_abs_path)
    
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

        unique_probe_types_str = unique_probe_types
            .collect()
            .map {
                it.join(',')
            }

        ctrl_fluorescence_plots_ch_out = CTRL_FLUORESCENCE_PLOTS(ctrl_fluorescence_data_ch_out.ctrl_fluorescence_data_path, sample_sheet_abs_path, unique_grouping_cols, unique_probe_types)
        ctrl_fluorescence_plot_paths = ctrl_fluorescence_plots_ch_out
            .collect()
            .map {
                it.join(',')
            }
    } else {
        ctrl_fluorescence_plot_paths = Channel.value("$projectDir/assets/no_ctrl_fluorescence.txt")
        unique_probe_types_str = Channel.value("no_probe_types")
    }

    // preprocess_ch_out.raw_mynorm_path: imputed mynorm path
    // preprocess_ch_out.preprocessing_data_summary: preprocessing data summary JSON file path
    preprocess_ch_out = PREPROCESS(input_abs_path, cpus, params.prep_code, params.collapse_prefix, params.collapse_prefix_method, sample_sheet_abs_path)
    
    // impute_ch_out.imputed_mynorm: imputed mynorm path
    // impute_ch_out.nan_per_sample: path to file with %NaN per sample stats
    // impute_ch_out.nan_per_probe: path to file with %NaN per probe stats
    // impute_ch_out.mynorm_imputed_n_cpgs: number of CpGs in imputed mynorm
    impute_ch_out = IMPUTE(preprocess_ch_out.raw_mynorm_path, params.p_threshold, params.s_threshold, params.imputer_type)

    if(impute_ch_out) {
        ADDITIONAL_VALIDATORS_AFTER_IMPUTE(params.n_rand_cpgs, params.nan_per_probe_n_cpgs, impute_ch_out.imputation_summary_path)
    }

    if(processed_samples_count > 10) {
        ao_results = ANOMALY_DETECTION(impute_ch_out.imputed_mynorm, params.contamination)
        ao_plot_path = ao_results.ao_plot
    } else {
        ao_plot_path = Channel.value("$projectDir/assets/no_ao_plot.txt")
    }

    // run sex_inference process when parameter infer_sex is set to true
    if(params.infer_sex) {
        sex_inference_path = SEX_INFERENCE(impute_ch_out.imputed_mynorm, cpus, sample_sheet_abs_path)
    } else {
        sex_inference_path = Channel.value("$projectDir/assets/no_sex_inference.txt")
    }

    beta_distr_ch_out = BETA_DISTRIBUTION(impute_ch_out.imputed_mynorm, params.n_rand_cpgs)

    batch_effect_ch_out = BATCH_EFFECT(impute_ch_out.imputed_mynorm, sample_sheet_abs_path, ["Sentrix_ID", "Sentrix_Position"], beta_distr_ch_out.n_rand_cpgs_path)

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

    nan_per_sample_ch_out = NAN_DISTRIBUTION_PER_SAMPLE(qc_ch_out.qc_parquet, sample_sheet_abs_path)
    
    nan_per_sample_plot_paths = nan_per_sample_ch_out
            .collect()
            .map {
                it.join(',')
            }

    nan_per_probe_plot = NAN_DISTRIBUTION_PER_PROBE(preprocess_ch_out.raw_mynorm_path, params.nan_per_probe_n_cpgs)

    if(processed_samples_count > 10) {
        // pca_ch_out.area: area plot path
        // pca_ch_out.scatter: scatter matrix plot paths
        // pca_ch_out.kruskal: Kruskal-Wallis test results
        pca_ch_out = PCA(impute_ch_out.imputed_mynorm, sample_sheet_abs_path, params.perc_pca_cpgs, params.pca_number_of_components, params.pca_columns, params.pca_matrix_PC_count)
        pca_plot_paths = pca_ch_out.scatter
            .merge(pca_ch_out.area)
            .collect()
            .map {
                it.join(',')
            }

        if(pca_ch_out.kruskal) {
            pca_kruskal_paths = pca_ch_out.kruskal
            .collect()
            .map {
                it.join(',')
            }
        } 
    } else {
        pca_kruskal_paths = Channel.value("$projectDir/assets/no_pca_kruskal.txt")
        pca_plot_paths = Channel.value("$projectDir/assets/no_pca_plot.txt")
    }

    if(params.infer_epi_age) {
        // epi_age_res_ch_out.epi_clocks_res_parquet - epigenetic age inference results (PARQUET)
        // epi_age_res_ch_out.epi_clocks_res_json - epigenetic age inference results (JSON)
        epi_age_res_ch_out = EPIGENETIC_AGE_INFERENCE(sample_sheet_abs_path, impute_ch_out.imputed_mynorm, params.epi_clocks)
        epi_age_plots_ch_out = EPIGENETIC_AGE_PLOTS(epi_age_res_ch_out.epi_clocks_res_parquet, sample_sheet_abs_path, params.epi_clocks?.split(',') as List)

        epi_age_paths = epi_age_plots_ch_out.regr
            .mix(epi_age_plots_ch_out.eaa)
            .mix(epi_age_plots_ch_out.eaa_post_hoc)
            .mix(epi_age_res_ch_out.epi_clocks_res_json)
            .collect()
            .map {
                it.join(',')
            }
    } else {
        epi_age_paths = Channel.value("$projectDir/assets/no_epi_age.txt")
    }

    report_template_path = file("${projectDir}/templates/report.html", checkIfExists: true)

    def workflowMeta = workflow

    def params_map_all = paramsSummaryMap(workflow)
    def params_path = file("${params.output}/params.json")

    def paramExporter = new JsonWorkflowParamExporter(
        params as HashMap,
        params_map_all,
        workflowMeta,
        nextflow.version.toString(),
        workflow_start
    )
    params_path.text = paramExporter.toJSON()

    REPORT(
        report_template_path,
        qc_ch_out.qc_json,
        ctrl_fluorescence_plot_paths,
        preprocess_ch_out.preprocess_summary_path,
        impute_ch_out.imputation_summary_path,
        ao_plot_path,
        beta_distr_ch_out.beta_distr_plot,
        nan_per_probe_plot,
        nan_per_sample_plot_paths,
        batch_effect_plot_paths,
        sex_inference_path,
        params_path,
        pca_kruskal_paths,
        pca_plot_paths,
        epi_age_paths,
        unique_probe_types_str
    )

    workflow.onComplete = {
        def formatter = java.time.format.DateTimeFormatter
            .ofPattern("dd MMMM yyyy HH:mm:ss", java.util.Locale.ENGLISH)
            .withZone(java.time.ZoneId.systemDefault())
        def startStr = formatter.format(workflow.start)
        def completeStr = formatter.format(workflow.complete)
        def totalSecs = java.time.Duration.between(workflow.start, workflow.complete).toSeconds()
        def h = totalSecs.intdiv(3600)
        def m = (totalSecs % 3600).intdiv(60)
        def s = totalSecs % 60
        def durationStr = "${h.toString().padLeft(2,'0')}:${m.toString().padLeft(2,'0')}:${s.toString().padLeft(2,'0')}"
        def runTimes = "${startStr} - ${completeStr} (duration: ${durationStr})"
        def reportFile = new File("${params.output}/qc_report.html")
        if (reportFile.exists()) {
            reportFile.text = reportFile.text.replace("__PIPELINE_RUN_TIMES__", runTimes)
        }
        println("Workflow completed")
    }

    workflow.onError = {
        // def params_map_all = paramsSummaryMap(workflow)
        // def idat_list_size = file("$input_abs_path/{*.idat,*.idat.gz}").size()
        // def paramExporter = new JsonWorkflowParamExporter()
        // file("${params.output}/params.json").text = paramExporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size, processed_samples_count)
        println("Workflow completed with errors")
    }


    /*
    Left here for now due to sometimes appearing error (unknown cause): 
    Variable `workflow` already defined in the process scope
    when this declaration is within workflow scope
    */
    log.info paramsSummaryLog(workflow)

    /* 
    Moved saving params to the end of the workflow to add parameters such as workflow duration etc.
    
    Temporary manual parameter map flattening - some of the options had to be removed as JSON conversion returned weird StackOverflow error when there were too many items in a map despite map flattening
    Structure flattening neccessary because of unresolved Nextflow bug: https://github.com/nextflow-io/nextflow/issues/2815
    
    Assignment of a handler neccessary due to unresolved Nextflow bug: https://github.com/nextflow-io/nextflow/issues/5261
    https://github.com/nextflow-io/nextflow/issues/5445
    */

    // Extract values from channels before workflow.onComplete
    // def qc_json_val
    // qc_ch_out.qc_json.view { qc_json_val = it }

    // def ctrl_fluor_vals
    // ctrl_fluorescence_plot_paths.view { ctrl_fluor_vals = it.join(",") }

    // def preprocess_summary_val
    // preprocess_ch_out.preprocess_summary_path.view { preprocess_summary_val = it }

    // def imputation_summary_val
    // impute_ch_out.imputation_summary_path.view { imputation_summary_val = it }

    // def ao_plot_val
    // ao_plot_path.view { ao_plot_val = it }

    // def beta_distr_plot_val
    // beta_distr_ch_out.beta_distr_plot.view { beta_distr_plot_val = it }

    // def nan_per_probe_plot_val
    // nan_per_probe_plot.view { nan_per_probe_plot_val = it }

    // def nan_per_sample_plot_vals
    // nan_per_sample_plot_paths.collect().view { nan_per_sample_plot_vals = it.join(",") }

    // def batch_effect_plot_vals
    // batch_effect_plot_paths.collect().view { batch_effect_plot_vals = it.join(",") }

    // def sex_inference_val
    // sex_inference_path.view { sex_inference_val = it }

    // def pca_kruskal_vals
    // pca_kruskal_paths.collect().view { pca_kruskal_vals = it.join(",") }

    // def pca_plot_vals
    // pca_plot_paths.collect().view { pca_plot_vals =  it.join(",")}

    // def epi_age_vals
    // epi_age_paths.collect().view { epi_age_vals = it.join(",") }

    // def unique_probe_types_str_val
    // unique_probe_types_str.collect().view { unique_probe_types_str_val = it.join(",") }

    // workflow.onComplete = {
    //     def params_map_all = paramsSummaryMap(workflow)
    //     def idat_list_size = file("$input_abs_path/{*.idat,*.idat.gz}").size()
    //     def param_exporter = new JsonWorkflowParamExporter()
        
    //     def params_json_str = param_exporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size, processed_samples_count)

    //     def report_template_path = file("${projectDir}/templates/report.html", checkIfExists: true)
        
    //     def params_path = new File("${params.output}/params.json")

    //     params_path.text = params_json_str

    //     println("Running final report generation...")

    //     def report_cmd = """
    //         docker run --rm -v $projectDir:$projectDir \
    //         -w $projectDir \
    //         janbinkowski96/methyl-array-qc-python \
    //         python3 bin/report.py \
    //         ${report_template_path.toString()} \
    //         ${qc_json_val.toString()} \
    //         ${ctrl_fluor_vals.toString()} \
    //         ${preprocess_summary_val.toString()} \
    //         ${imputation_summary_val.toString()} \
    //         ${ao_plot_val.toString()} \
    //         ${beta_distr_plot_val.toString()} \
    //         ${nan_per_probe_plot_val.toString()} \
    //         ${nan_per_sample_plot_vals.toString()} \
    //         ${batch_effect_plot_vals.toString()} \
    //         ${sex_inference_val.toString()} \
    //         ${params_path.toString()} \
    //         ${pca_kruskal_vals.toString()} \
    //         ${pca_plot_vals.toString()} \
    //         ${epi_age_vals.toString()} \
    //         ${unique_probe_types_str_val.toString()}
    //     """
    //     println "Executing: ${report_cmd}"
    //     report_cmd.execute().waitFor()
    //     //proc.in.eachLine { println it }
    //     // proc.err.eachLine { System.err.println it }
    //     // proc.waitFor()

    //     println("Workflow completed")
    // }

    // workflow.onError = {
    //     def params_map_all = paramsSummaryMap(workflow)
    //     def idat_list_size = file("$input_abs_path/{*.idat,*.idat.gz}").size()
    //     def param_exporter = new JsonWorkflowParamExporter()
        
    //     def params_json_str = param_exporter.toJSON(params, params_map_all, workflow, nextflow.version, idat_list_size, processed_samples_count)

    //     def report_template_path = file("${projectDir}/templates/report.html", checkIfExists: true)
        
    //     def params_path = new File("${params.output}/params.json")

    //     params_path.text = params_json_str

    //     println("Running final report generation...")

    //     // better solution: divide workflow into subworkflows (analysis and report separately) and export only analysis stats?
    //     // def report_cmd = """
    //     //     docker run --rm -v $projectDir:$projectDir \
    //     //     -w $projectDir \
    //     //     janbinkowski96/methyl-array-qc-python \
    //     //     python3 bin/report.py \
    //     //     ${report_template_path.toString()} \
    //     //     ${qc_json_val.toString()} \
    //     //     ${ctrl_fluor_vals.toString()} \
    //     //     ${preprocess_summary_val.toString()} \
    //     //     ${imputation_summary_val.toString()} \
    //     //     ${ao_plot_val.toString()} \
    //     //     ${beta_distr_plot_val.toString()} \
    //     //     ${nan_per_probe_plot_val.toString()} \
    //     //     ${nan_per_sample_plot_vals.toString()} \
    //     //     ${batch_effect_plot_vals.toString()} \
    //     //     ${sex_inference_val.toString()} \
    //     //     ${params_path.toString()} \
    //     //     ${pca_kruskal_vals.toString()} \
    //     //     ${pca_plot_vals.toString()} \
    //     //     ${epi_age_vals.toString()} \
    //     //     ${unique_probe_types_str_val.toString()}
    //     // """

    //     // def report_cmd = [
    //     //     "python", "report.py",
    //     //     report_template_path.toString(),
    //     //     qc_json_val.toString(),
    //     //     ctrl_fluor_vals.toString(),
    //     //     preprocess_summary_val.toString(),
    //     //     imputation_summary_val.toString(),
    //     //     ao_plot_val.toString(),
    //     //     beta_distr_plot_val.toString(),
    //     //     nan_per_probe_plot_val.toString(),
    //     //     nan_per_sample_plot_vals.toString(),
    //     //     batch_effect_plot_vals.toString(),
    //     //     sex_inference_val.toString(),
    //     //     params_path.toString(),
    //     //     pca_kruskal_vals.toString(),
    //     //     pca_plot_vals.toString(),
    //     //     epi_age_vals.toString(),
    //     //     unique_probe_types_str_val.toString()
    //     // ]
    //     println "Executing: ${report_cmd}"
    //     report_cmd.execute().waitFor()
    //     // proc.in.eachLine { println it }
    //     // proc.err.eachLine { System.err.println it }
    //     // proc.waitFor()

    //     println("Workflow completed with errors")
    // }
}
