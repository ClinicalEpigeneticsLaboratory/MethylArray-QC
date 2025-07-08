#!/usr/local/bin/python

"""
A module generating batch effect evaluation figures
"""

import sys
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plot_export_utils import export_decorated_fig_with_custom_name


def get_single_fig(
    sample_sheet: pd.DataFrame,
    grouped: pd.DataFrame,
    row_num: int,
    column: str,
) -> go.Figure:
    """A function generating a single batch effect evaluation figure

    Args:
        sample_sheet (pd.DataFrame): sample sheet
        grouped (pd.DataFrame): plot data (data from imputed mynorm\
            and sample sheet, grouped by processed column)
        row_num (int): currently processed number of plot row (set of column items)
        column (str): currently processed column

    Returns:
        go.Figure: a single figure for specific column and set of column items
    """
    ids_to_plot = list(sample_sheet.loc[sample_sheet["Plot_num"] == row_num, column])

    # Check if we have valid Sentrix_IDs to plot
    if ids_to_plot:
        # Selecting columns for the boxplot
        grouped_row = grouped.loc[:, ids_to_plot]

        # Reset the index to include CpG as a column
        grouped_row_reset = grouped_row.reset_index(names="CpG")

        # Melt the grouped row into long format for plotly
        grouped_row_melted = (
            grouped_row_reset
            .melt(id_vars="CpG", var_name=column, value_name="Mean beta value")
            .assign(**{"Mean beta value": lambda df: df["Mean beta value"].round(4)})
        )

        grouped_row_melted["Mean beta value"] = grouped_row_melted["Mean beta value"].astype(np.float32)

        n_cpgs_plotted = grouped_row_melted["CpG"].nunique()

        # cpgs = grouped_row_reset["CpG"].values
        # sample_ids = grouped_row_reset.columns.drop("CpG").tolist()
        # values = grouped_row_reset.drop(columns="CpG").to_numpy(dtype=np.float32)
        # values = np.round(values, 4).astype(np.float32)

        # Create the long-format data manually for plotly
        # long_data = {
        #     column: [],
        #     "Mean beta value": [],
        #     "CpG": [],
        # }

        # for i, sid in enumerate(sample_ids):
        #     long_data[column].extend([sid] * len(cpgs))
        #     long_data["Mean beta value"].extend(values[:, i])
        #     long_data["CpG"].extend(cpgs)

        # Now create the plot using the dict
        # fig = px.box(long_data, x=column, y="Mean beta value")

        # fig = go.Figure()
        # for group, group_df in grouped_row_melted.groupby(column):
        #     fig.add_trace(go.Box(
        #         y=group_df["Mean beta value"],
        #         name=str(group),
        #         boxpoints=False  # Don't show raw points
        #     ))
        fig = px.box(grouped_row_melted, x=column, y="Mean beta value")
        fig.update_layout(boxgap=0.05, title=f"n = {n_cpgs_plotted} randomly selected CpGs",)
        fig.update_xaxes(tickangle=90)
    else:
        print(f"Warning: No {column}s found for row {row_num}.")
    return fig


def get_all_figs(
    path_to_imputed_mynorm: str,
    path_to_sample_sheet: str,
    column: str,
    path_to_n_rand_cpgs: str
) -> None:
    """A function generating all batch effect figures, in a loop

    Args:
        path_to_imputed_mynorm (str): path to imputed mynorm
        path_to_sample_sheet (str): path to sample sheet
        column (str): currently processed column
        path_to_n_rand_cpgs (str): path to a file with a list of randomly saelected n CpGs used in this analysis and for beta distribution plot
    """
    # Load data
    with open(path_to_n_rand_cpgs, "r", encoding="utf-8") as f:
        n_rand_cpgs = json.load(f)

    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    filtered_imp_mynorm = imputed_mynorm.loc[imputed_mynorm.index.intersection(n_rand_cpgs)]

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[["Sentrix_ID", "Sentrix_Position"]] = sample_sheet[
        "Array_Position"
    ].str.split("_", expand=True)

    # compute the number of figures to generate and assign each
    # Sentrix_ID/Sentrix_Position to a specific subplot
    sample_sheet["row_id"] = range(1, sample_sheet.index.size + 1)
    sample_sheet["Plot_num"] = (sample_sheet["row_id"] - 1) // 10 + 1

    data = pd.concat((filtered_imp_mynorm.T, sample_sheet[column]), axis=1)

    # Create figure
    grouped = data.groupby(column).mean().T

    for row_num in sample_sheet["Plot_num"].unique():
        fig = get_single_fig(
            column=column,
            grouped=grouped,
            row_num=row_num,
            sample_sheet=sample_sheet,
        )

        if fig is not None:
            export_decorated_fig_with_custom_name(
                fig=fig,
                json_path=f"{column}_{row_num}.json",
            )


def main():
    if len(sys.argv) != 5:
        print(
            "Usage: python batch_effect.py <path_to_imputed_mynorm: str> \
                <path_to_sample_sheet: str> <column: str> <n_rand_cpgs_path: str>"
        )
        sys.exit(1)

    imputed_mynorm_path = sys.argv[1]
    sample_sheet_path = sys.argv[2]
    col = str(sys.argv[3])
    n_rand_cpgs_path = sys.argv[4]

    get_all_figs(
        path_to_imputed_mynorm=imputed_mynorm_path,
        path_to_sample_sheet=sample_sheet_path,
        column=col,
        path_to_n_rand_cpgs=n_rand_cpgs_path
    )


if __name__ == "__main__":
    main()
