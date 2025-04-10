process EPIGENETIC_AGE_PLOTS {
    publishDir "${params.output}", mode: 'copy', overwrite: true
    label 'python'

    input:
    path epi_age_res_path
    path sample_sheet_path
    each epi_clock

    output:
    path "Regression/Regr_Age_vs_Epi_Age_${epi_clock}.json", arity: "1..*", emit: regr
    path "EAA/Epi_Age_Accel_${epi_clock}.json", optional: true, emit: eaa

    script:
    """
    epigenetic_age_plots.py ${epi_age_res_path} ${sample_sheet_path} ${epi_clock}
    """
}
