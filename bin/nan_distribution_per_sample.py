#!/usr/local/bin/python

import sys

import pandas as pd
import plotly.express as px


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python nan_distribution_per_sample.py <path_to_qc_stats> <path_to_sample_sheet>"
        )
        sys.exit(1)

    path_to_qc_stats = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]

    # Load data
    qc = pd.read_parquet(path_to_qc_stats)
    sample_sheet = pd.read_csv(path_to_sample_sheet)

    # From SeSAME documentation - frac_na is computed as:
    # s$frac_na <- sum(is.na(betas)) / length(betas)

    # Computation of perc_na:
    qc["perc_na"] = qc["frac_na"] * 100
    data = qc.merge(sample_sheet, on="Sample_Name")

    # Figure generation
    fig = px.bar(
        data, x="Sample_Name", y="perc_na", hover_data=sample_sheet.columns.to_list()
    )

    fig.update_yaxes(title="% NaN", range=[0, 100])
    fig.update_layout(
        width=600,
        height=300,
        template="ggplot2",
        title_text="NaN% per sample",
        showlegend=False,
    )
    fig.write_json(file="nan_distribution_per_sample.json", pretty=True)


if __name__ == "__main__":
    main()
