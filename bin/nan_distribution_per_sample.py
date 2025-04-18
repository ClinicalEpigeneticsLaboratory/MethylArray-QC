#!/usr/local/bin/python

from decorators import update_and_export_plot

import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

@update_and_export_plot(json_path = "nan_distribution_per_sample.json", showlegend = False, height = 400)
def getNaNDistrPerSamplePlot(plot_data: pd.DataFrame, hover_data: list) -> go.Figure:
    # Figure generation
    fig = px.bar(
        plot_data, 
        x = "Sample_Name", 
        y = "% NaN", 
        hover_data = hover_data,
    )

    fig.update_yaxes(title="% NaN", range=[0, 100])
    fig.update_layout(title_text="% NaN per sample",  
                    margin={"t": 75}
    )

    return fig

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
    qc["% NaN"] = qc["frac_na"] * 100
    data = qc.merge(sample_sheet, on="Sample_Name")

    getNaNDistrPerSamplePlot(plot_data = data, hover_data = sample_sheet.columns.to_list())

if __name__ == "__main__":
    main()
