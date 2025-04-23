process EPIGENETIC_AGE_PLOTS {
    publishDir "${params.output}/Epi_age/Plots/Regression", mode: 'copy', overwrite: true, pattern: 'Regr_Age_vs_Epi_Age_*.json'
    publishDir "${params.output}/Epi_age/Plots/Accel", mode: 'copy', overwrite: true, pattern: 'Epi_Age_Accel_*.json'
    label 'python'

    input:
    path epi_age_res_path
    path sample_sheet_path
    each epi_clock

    output:
    path "Regr_Age_vs_Epi_Age_${epi_clock}.json", arity: "1..*", emit: regr
    path "Epi_Age_Accel_${epi_clock}.json", optional: true, arity: "1..*", emit: eaa

    script:
    """
    epigenetic_age_plots.py ${epi_age_res_path} ${sample_sheet_path} ${epi_clock}
    """
}
