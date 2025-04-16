#!/usr/local/bin/python

import json
import sys
from pathlib import Path

import pandas as pd


def validateParamsRandomCpGCount(
    n_cpgs: int, imputed_mynorm_n_cpgs: int, param_name: str
) -> None:
    assert (
        n_cpgs <= imputed_mynorm_n_cpgs
    ), f"{param_name}: random number of CpGs ({n_cpgs}) is larger than CpG count in imputed mynorm ({imputed_mynorm_n_cpgs})!"


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python additional_validators_after_impute.py <params_n_cpgs_beta_distr: int> <params_nan_per_probe_n_cpgs: int> <imputed_mynorm_n_cpgs_path: Path>"
        )
        sys.exit(1)

    params_n_cpgs_beta_distr = int(sys.argv[1])
    params_nan_per_probe_n_cpgs = int(sys.argv[2])
    imputed_mynorm_n_cpgs_path = Path(sys.argv[3])

    imputed_mynorm_n_cpgs_dict = {}
    with open(imputed_mynorm_n_cpgs_path) as f:
        imputed_mynorm_n_cpgs_dict = json.load(f)
    imputed_mynorm_n_cpgs = imputed_mynorm_n_cpgs_dict["mynorm_imputed_n_cpgs"]

    validateParamsRandomCpGCount(
        param_name=f"{params_n_cpgs_beta_distr=}".split("=")[0],
        n_cpgs=params_n_cpgs_beta_distr,
        imputed_mynorm_n_cpgs=imputed_mynorm_n_cpgs,
    )

    validateParamsRandomCpGCount(
        param_name=f"{params_nan_per_probe_n_cpgs=}".split("=")[0],
        n_cpgs=params_nan_per_probe_n_cpgs,
        imputed_mynorm_n_cpgs=imputed_mynorm_n_cpgs,
    )


if __name__ == "__main__":
    main()
