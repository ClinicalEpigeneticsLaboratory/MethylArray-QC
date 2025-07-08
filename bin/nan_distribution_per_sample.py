#!/usr/local/bin/python

"""
A module generating a barplot presenting the percentage of
missing values per sample
"""

import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plot_export_utils import export_decorated_fig_with_custom_name

def get_all_figs(
    qc_path: str,
    sample_sheet_path: str,
) -> None:
    """A function generating all %NaN per sample figures, in a loop

    Args:
        qc_path (str): path to QC stats generated with SeSAME (process: QC)
        sample_sheet_path (str): path to sample sheet
    """
    
    # Load data
    qc = pd.read_parquet(qc_path)
    sample_sheet = pd.read_csv(sample_sheet_path)

    # From SeSAME documentation - frac_na is computed as:
    # s$frac_na <- sum(is.na(betas)) / length(betas)

    # Computation of perc_na:
    qc["% NaN"] = qc["frac_na"] * 100

    # compute the number of figures to generate and assign each
    # sample to a specific subplot
    sample_sheet["row_id"] = range(1, sample_sheet.index.size + 1)
    sample_sheet["Plot_num"] = (sample_sheet["row_id"] - 1) // 10 + 1

    data = qc.merge(sample_sheet, on="Sample_Name")

    for row_num in sample_sheet["Plot_num"].unique():
        fig = get_single_fig(
            row_num=row_num,
            sample_sheet=sample_sheet,
            plot_data=data,
        )

        if fig is not None:
            export_decorated_fig_with_custom_name(
                fig=fig,
                json_path=f"nan_distribution_per_sample_{row_num}.json",
            )

def get_single_fig(
    sample_sheet: pd.DataFrame,
    plot_data: pd.DataFrame, 
    row_num: int,
) -> go.Figure:
    """A function generating a barplot presenting the percentage of
    missing values per sample

        Args:
            sample_sheet (pd.DataFrame): sample sheet
            plot_data (pd.DataFrame): data used to generate the plot
            hover_data (list): list of columns displayed in hover data
            row_num (int): currently processed number of plot row (set of samples)

        Returns:
            go.Figure: a barplot
    """
    ids_to_plot = list(sample_sheet.loc[sample_sheet["Plot_num"] == row_num, "Sample_Name"])

    row_plot_data = plot_data[plot_data["Sample_Name"].isin(ids_to_plot)]

    # Check if we have valid sample names to plot
    if ids_to_plot:
        # Figure generation
        fig = px.bar(
            row_plot_data,
            x="Sample_Name",
            y="% NaN",
            hover_data=sample_sheet.columns.to_list(),
        )

        fig.update_yaxes(title="% NaN", range=[0, 100])
        fig.update_layout(title_text="% NaN per sample", margin={"t": 75})

        return fig


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python nan_distribution_per_sample.py <path_to_qc_stats: str> \
                <path_to_sample_sheet: str>"
        )
        sys.exit(1)

    path_to_qc_stats = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]

    get_all_figs(
        qc_path=path_to_qc_stats,
        sample_sheet_path = path_to_sample_sheet
    )

    # get_nan_distr_per_sample_plot(
    #     plot_data=data, hover_data=sample_sheet.columns.to_list()
    # )


if __name__ == "__main__":
    main()
