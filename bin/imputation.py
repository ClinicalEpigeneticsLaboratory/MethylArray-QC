#!/usr/local/bin/python

import sys
import pandas as pd
from sklearn.impute import SimpleImputer, KNNImputer


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: python imputation.py <path_to_mynorm> <p_threshold> <s_threshold> <imputer_type>"
        )
        sys.exit(1)

    path_to_mynorm = sys.argv[1]
    p_threshold = float(sys.argv[2])
    s_threshold = float(sys.argv[3])
    imputer_type = sys.argv[4]

    # Load data
    mynorm = pd.read_parquet(path_to_mynorm)
    mynorm.set_index("CpG", inplace=True)

    nan_per_sample = (mynorm.isna().sum(axis=0) / mynorm.index.size) * 100
    nan_per_sample_df = pd.DataFrame(
        {
            'Sample_Name': nan_per_sample.index,
            'NaN_percent': nan_per_sample.values
        }
    )
    nan_per_sample_df.to_parquet("impute_nan_per_sample.parquet")

    nan_per_cpg = (mynorm.isna().sum(axis=1) / mynorm.columns.size) * 100
    nan_per_cpg_df = pd.DataFrame(
        {
            'CpG': nan_per_cpg.index,
            'NaN_percent': nan_per_cpg.values
        }
    )
    nan_per_cpg_df.to_parquet("impute_nan_per_probe.parquet")

    # Remove probes with too many NaN values
    mynorm = mynorm.loc[mynorm.isnull().mean(axis=1) < p_threshold]

    # Remove samples with too many NaN values
    mynorm = mynorm.loc[:, mynorm.isnull().mean(axis=0) < s_threshold]

    # Impute remaining missing values
    if imputer_type == "mean":
        imputer = SimpleImputer(strategy="mean")
    elif imputer_type == "median":
        imputer = SimpleImputer(strategy="median")
    elif imputer_type == "knn":
        imputer = KNNImputer()
    else:
        print("Invalid imputer_type. Use 'mean', 'median', or 'knn'.")
        sys.exit(1)

    mynorm_imputed = pd.DataFrame(
        imputer.fit_transform(mynorm), index=mynorm.index, columns=mynorm.columns
    )

    # Save the imputed data
    mynorm_imputed = mynorm_imputed.reset_index()
    mynorm_imputed.to_parquet("imputed_mynorm.parquet")


if __name__ == "__main__":
    main()
