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
    filtered_mynorm: pd.DataFrame,
    row_num: int,
    column: str,
) -> go.Figure:
    """A function generating a single batch effect evaluation figure

    Args:
        sample_sheet (pd.DataFrame): sample sheet
        filtered_mynorm (pd.DataFrame): imputed mynorm containing only randomly selected n CpGs
        row_num (int): currently processed number of plot row (set of column items)
        column (str): currently processed column

    Returns:
        go.Figure: a single figure for specific column and set of column items
    """
    fig = None  # initialize to avoid reference before assignment
    ids_to_plot = list(sample_sheet.loc[sample_sheet["Plot_num"] == row_num, column])

    # Check if we have valid Sentrix_IDs to plot
    if ids_to_plot:
        row_sample_sheet = sample_sheet.loc[sample_sheet[column].isin(ids_to_plot), :]

        sample_ids = row_sample_sheet["Sample_Name"]
        
        row_mynorm = filtered_mynorm.loc[:, sample_ids]
        
        row_sample_sheet_indexed = row_sample_sheet.set_index("Sample_Name")

        row_mynorm_T = row_mynorm.T
        row_mynorm_T.index.name = "Sample_Name"

        data = row_mynorm_T.join(row_sample_sheet_indexed[[column]], how="inner")

        grouped_row = data.groupby(column).mean().T

        grouped_row_reset = grouped_row.reset_index(names="CpG")

        # Melt the grouped row into long format for plotly
        grouped_row_melted = (
            grouped_row_reset
            .melt(id_vars="CpG", var_name=column, value_name="Mean beta value")
            .assign(**{"Mean beta value": lambda df: df["Mean beta value"].round(4)})
        )
        grouped_row_melted["Mean beta value"] = grouped_row_melted["Mean beta value"].astype(np.float32)

        if not grouped_row_melted["Mean beta value"].notna().any():
            print(f"All mean beta values are NaN for {column} row {row_num}. Skipping plot.")
            return None

        fig = px.box(grouped_row_melted, x=column, y="Mean beta value")
        fig.update_layout(boxgap=0.05)
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
    unique_ids = sample_sheet[[column]].drop_duplicates().reset_index(drop=True)
    unique_ids["Plot_num"] = (unique_ids.index // 10) + 1
    
    sample_sheet = sample_sheet.reset_index()
    sample_sheet = sample_sheet.merge(unique_ids, on=column, how="left")

    for row_num in sample_sheet["Plot_num"].unique():
        fig = get_single_fig(
            column=column,
            filtered_mynorm = filtered_imp_mynorm,
            row_num=row_num,
            sample_sheet=sample_sheet,
        )

        if fig is not None:
            print(f"✅ Writing plot to: {column}_{row_num}.json")
            export_decorated_fig_with_custom_name(
                fig=fig,
                json_path=f"{column}_{row_num}.json",
            )
        else:
            print(f"⚠️ No figure generated for {column}, row {row_num}.")


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
