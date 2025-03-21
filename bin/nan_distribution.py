#!/usr/local/bin/python

import sys
import pandas as pd
import plotly.express as px

def main():
    if len(sys.argv) != 2:
        print("Usage: python nan_distribution.py <path_to_qc_stats>")
        sys.exit(1)

    path_to_qc_stats = sys.argv[1]

    # Load data
    qc = pd.read_parquet(path_to_qc_stats)

    # From SeSAME documentation - frac_na is computed as:
    # s$frac_na <- sum(is.na(betas)) / length(betas)
    
    # Computation of perc_na:
    qc["perc_na"] = qc["frac_na"] * 100

    # Figure generation
    fig = px.bar(qc, x='Sample', y='perc_na')

    fig.update_yaxes(title = "% NaN", range = [0, 100])
    fig.update_layout(width = 600, height = 300, template = "ggplot2", title_text = "NaN% per sample", showlegend = False)
    fig.write_json(file = "nan_distribution.json")

if __name__ == "__main__":
    main()