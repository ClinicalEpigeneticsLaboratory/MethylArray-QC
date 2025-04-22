#!/usr/local/bin/python

"""
Module performing additional parameter validation
(apart from the one managed by Nextflow Schema)
for parameters not depending on imputation statistics
(validation can be performed at workflow start)
"""

import multiprocessing
import sys
from pathlib import Path

import pandas as pd


def validate_params_input(in_dir: Path) -> None:
    """Function validating input directory parameter"""
    assert in_dir.exists(), "Input does not exists!"
    assert in_dir.is_dir(), "Input is not a directory!"

    idat_files = [
        file for file in in_dir.iterdir() if file.suffix in [".idat", ".idat.gz"]
    ]
    idat_list_size = len(idat_files)

    assert idat_list_size > 0, "Input directory does not contain IDAT files!"
    assert (
        idat_list_size % 2 == 0
    ), """Number of IDAT files in input directory is not \
    a multiplication of 2 and there should be 2 IDATs per \
    one sample - did you forget to copy some files?"""


def validate_params_cpus(cpus: int) -> None:
    """Function validating cpus parameter"""
    max_available_cpus = multiprocessing.cpu_count()

    assert cpus != 0, "params.cpus cannot be equal to 0!"
    assert (
        cpus <= max_available_cpus
    ), "params.cpus cannot be larger than $max_available_cpus!"


def validate_params_pca(
    sample_sheet_path: Path, pca_number_of_components: int, pca_matrix_pc_count: int
) -> None:
    """Function validating parameters used by PCA module"""
    sample_sheet = pd.read_csv(sample_sheet_path)
    sample_count = sample_sheet.index.size

    assert (
        pca_number_of_components <= sample_count
    ), f"params.pca_number_of_components must be below {sample_count} (sample count)!"
    assert (
        pca_matrix_pc_count <= sample_count
    ), f"params.pca_matrix_PC_count must be below {sample_count} (sample count)!"
    assert (
        pca_matrix_pc_count <= pca_number_of_components
    ), f"""params.pca_matrix_PC_count ({pca_matrix_pc_count}) must be \
    <= params.pca_number_of_components ({pca_number_of_components})!"""


def main():
    if len(sys.argv) != 6:
        print(
            """Usage: python additional_validators_init.py <params_input> <params_sample_sheet> 
            <params_cpus> <params_pca_number_of_components> <params_pca_matrix_PC_count>"""
        )
        sys.exit(1)

    params_input = Path(sys.argv[1]).resolve()
    params_sample_sheet = Path(sys.argv[2]).resolve()
    params_cpus = int(sys.argv[3])
    params_pca_number_of_components = int(sys.argv[4])
    params_pca_matrix_pc_count = int(sys.argv[5])

    validate_params_input(in_dir=params_input)
    validate_params_cpus(cpus=params_cpus)
    validate_params_pca(
        sample_sheet_path=params_sample_sheet,
        pca_number_of_components=params_pca_number_of_components,
        pca_matrix_pc_count=params_pca_matrix_pc_count,
    )


if __name__ == "__main__":
    main()
