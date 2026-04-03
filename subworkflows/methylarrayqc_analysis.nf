workflow methylarrayqc_analysis {
    take:
        input_abs_path
        sample_sheet_abs_path
        cpus
        collapse_prefix
        collapse_prefix_method
        p_threshold
        s_threshold
        prep_code
        ctrl_intens_plots
        ctrl_intens_metric
        ctrl_intens_cols
        imputer_type
        contamination
        n_rand_cpgs
        nan_per_probe_n_cpgs
        perc_pca_cpgs
        contamination
        pca_number_of_components
        pca_columns
        pca_matrix_PC_count
        infer_sex
        infer_epi_age
        epi_clocks
    main:
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
            // previously: epi_age_res_path
            // epi_age_res_ch_out.epi_clocks_res_parquet - epigenetic age inference results (PARQUET)
            // TO CONSIDER: epi_age_res_ch_out.epi_clocks_res_json - epigenetic age inference results (JSON)
            epi_age_res_ch_out = EPIGENETIC_AGE_INFERENCE(sample_sheet_abs_path, impute_ch_out.imputed_mynorm, params.epi_clocks)
            epi_age_plots_ch_out = EPIGENETIC_AGE_PLOTS(epi_age_res_ch_out.epi_clocks_res_parquet, sample_sheet_abs_path, params.epi_clocks?.split(',') as List)

            epi_age_paths = epi_age_plots_ch_out.regr
                .merge(epi_age_plots_ch_out.eaa)
                .merge(epi_age_plots_ch_out.eaa_post_hoc)
                .collect()
                .map {
                    it.join(',')
                }
        } else {
            epi_age_paths = Channel.value("$projectDir/assets/no_epi_age.txt")
        }

        report_template_path = file("${projectDir}/templates/report.html", checkIfExists: true)
        params_path = file("${params.output}/params.json")
    emit:
}