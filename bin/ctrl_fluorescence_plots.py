#!/usr/local/bin/python

# TODO: there is a bug when a probe type consists of 2 words without underscore!!!

"""
A module generating figures for control probe fluorescence evaluation
"""

import sys

import pandas as pd
import plotly.express as px
from plot_export_utils import export_decorated_fig_with_custom_name

def get_ctrl_fluorescence_plot(
    plot_data: pd.DataFrame, 
    ctrl_probe_type: str, 
    column: str, 
    hover_cols: list
) -> None:
    """A function generating control probe fluorescence plot, with coloring by Sample_Group if this column is provided

    Args:
        plot_data (pd.DataFrame): data used to generate a plot
        ctrl_probe_type (str): a category of control probes (available categories depend on microarray type)
        column (str): a column, by which samples will be grouped at the plot
        hover_cols (list): a list of variables shown in a hover over sample point
    """    
    
    probe_data = plot_data[plot_data['Type'] == ctrl_probe_type]
    
    if "Sample_Group" in probe_data.columns:
        fig = px.scatter(
            probe_data, x=column, y="log_10_metric", hover_data=hover_cols, color = "Sample_Group", symbol = "Subtype"
        )
    else:
        fig = px.scatter(
            probe_data, x=column, y="log_10_metric", hover_data=hover_cols, symbol = "Subtype"
        )

    if probe_data['metric_type'].unique().tolist() == "total":
        metric_name = "Total Intensity"
    else:
        metric_name = "Max Intensity"

    fig.update_layout(
        yaxis={"title": f"log<sub>10</sub>{metric_name}<br>({ctrl_probe_type})"},
        legend={
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "orientation": "h",
        },
        scattermode="group",
    )

    if fig is not None:
        export_decorated_fig_with_custom_name(
            fig=fig,
            json_path=f"{ctrl_probe_type}_by_{column}.json",
        )

def main():
    if len(sys.argv) != 5:
        print(
            "Usage: python ctrl_fluorescence_plots.py <path_to_ctrl_fluorescence_data: str> \
                <path_to_sample_sheet: str> <column: str> <ctrl_probe_type: str>"
        )
        sys.exit(1)

    path_to_ctrl_fluorescence_data = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    column = sys.argv[3]
    ctrl_probe_type = sys.argv[4]

    ctrl_fluorescence_data_raw = pd.read_parquet(path_to_ctrl_fluorescence_data)
    
    sample_sheet = pd.read_csv(path_to_sample_sheet)
    sample_sheet[["Sentrix_ID", "Sentrix_Position"]] = sample_sheet[
        "Array_Position"
    ].str.split("_", expand=True)

    ctrl_fluorescence_data = ctrl_fluorescence_data_raw.merge(sample_sheet, on="Sample_Name")

    get_ctrl_fluorescence_plot(
        plot_data=ctrl_fluorescence_data,
        ctrl_probe_type=ctrl_probe_type,
        column=column,
        hover_cols=sample_sheet.columns.to_list(),
    )

if __name__ == "__main__":
    main()