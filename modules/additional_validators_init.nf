process ADDITIONAL_VALIDATORS_INIT {
    
    label 'python'
    
    input:
    path params_input
    path params_sample_sheet
    val params_cpus
    val params_pca_number_of_components
    val params_pca_matrix_PC_count

    script:
    """
    additional_validators_init.py $params_input $params_sample_sheet $params_cpus $params_pca_number_of_components $params_pca_matrix_PC_count
    """
}

// process ADDITIONAL_PARAM_VALIDATION {
    
//     output:
//     val idat_list_size, emit: idat_list_size

//     script: 
//     input_dir = file(params.input)
//     idat_list_size = file("$params.input/{*.idat,*.idat.gz}").size()
//     max_available_cpus = Runtime.runtime.availableProcessors()
//     sample_sheet = samplesheetToList(params.sample_sheet, "sample_sheet_schema.json")

//     // // params.input and its contents
//     // assert input_dir.isDirectory() : "Input is not a directory!"
    
//     // assert idat_list_size > 0 : "Input directory does not contain IDAT files!"
//     // assert idat_list_size % 2 == 0 : "Number of IDAT files in input directory is not a multiplication of 2 and there should be 2 IDATs per one sample - did you forget to copy some files?"
    
//     // //params.cpus
//     // assert params.cpus != 0 : "params.cpus cannot be equal to 0!"
//     // assert params.cpus <= max_available_cpus : "params.cpus cannot be larger than $max_available_cpus!"

//     // println(sample_sheet)
//     //TODO: n_cpgs_beta_distr, nan_per_probe_n_cpgs, pca_number_of_components, pca_matrix_PC_count
    
    
// }