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


# def get_single_fig(
#     sample_sheet: pd.DataFrame,
#     grouped: pd.DataFrame,
#     row_num: int,
#     column: str,
# ) -> go.Figure:
#     """A function generating a single batch effect evaluation figure

#     Args:
#         sample_sheet (pd.DataFrame): sample sheet
#         grouped (pd.DataFrame): plot data (data from imputed mynorm\
#             and sample sheet, grouped by processed column)
#         row_num (int): currently processed number of plot row (set of column items)
#         column (str): currently processed column

#     Returns:
#         go.Figure: a single figure for specific column and set of column items
#     """
#     ids_to_plot = sample_sheet.loc[sample_sheet["Plot_num"] == row_num, column].unique().tolist()
#     #grouped_row = grouped.loc[:, grouped.columns.intersection(ids_to_plot)]

#     # Check if we have valid Sentrix_IDs to plot
#     if ids_to_plot:
#         # Selecting columns for the boxplot
#         #grouped_row = grouped.loc[:, grouped.columns.intersection(ids_to_plot)]
#         grouped_row = grouped.loc[:, ids_to_plot]
#         rows, cols = grouped_row.shape
#         print(f"The grouped_row has {rows} rows and {cols} columns.")

#         # Reset the index to include CpG as a column
#         grouped_row_reset = grouped_row.reset_index(names="CpG")

#         # Melt the grouped row into long format for plotly
#         grouped_row_melted = (
#             grouped_row_reset
#             .melt(id_vars="CpG", var_name=column, value_name="Mean beta value")
#             .assign(**{"Mean beta value": lambda df: df["Mean beta value"].round(4)})
#         )

#         grouped_row_melted["Mean beta value"] = grouped_row_melted["Mean beta value"].astype(np.float32)

#         rows, cols = grouped_row_melted.shape
#         print(f"The grouped_row_melted has {rows} rows and {cols} columns.")

#         n_cpgs_plotted = grouped_row_melted["CpG"].nunique()

#         # cpgs = grouped_row_reset["CpG"].values
#         # sample_ids = grouped_row_reset.columns.drop("CpG").tolist()
#         # values = grouped_row_reset.drop(columns="CpG").to_numpy(dtype=np.float32)
#         # values = np.round(values, 4).astype(np.float32)

#         # Create the long-format data manually for plotly
#         # long_data = {
#         #     column: [],
#         #     "Mean beta value": [],
#         #     "CpG": [],
#         # }

#         # for i, sid in enumerate(sample_ids):
#         #     long_data[column].extend([sid] * len(cpgs))
#         #     long_data["Mean beta value"].extend(values[:, i])
#         #     long_data["CpG"].extend(cpgs)

#         # Now create the plot using the dict
#         # fig = px.box(long_data, x=column, y="Mean beta value")

#         # fig = go.Figure()
#         # for group, group_df in grouped_row_melted.groupby(column):
#         #     fig.add_trace(go.Box(
#         #         y=group_df["Mean beta value"],
#         #         name=str(group),
#         #         boxpoints=False  # Don't show raw points
#         #     ))
#         #
#         fig = px.box(grouped_row_melted, x=column, y="Mean beta value")
#         #fig = px.box(filte, x=column, y="Mean beta value")
#         fig.update_layout(boxgap=0.05, title=f"n = {n_cpgs_plotted} randomly selected CpGs",)
#         fig.update_xaxes(tickangle=90)
#     else:
#         print(f"Warning: No {column}s found for row {row_num}.")
#     return fig
def get_single_fig(
    sample_sheet: pd.DataFrame,
    filtered_mynorm: pd.DataFrame,
    #grouped: pd.DataFrame,
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
        row_sample_sheet = sample_sheet.loc[sample_sheet[column].isin(ids_to_plot), :]
        
        print("row_sample_sheet[column]:")
        print(row_sample_sheet[column].value_counts(dropna=False))

        # print("3")
        # print(row_sample_sheet.columns)
        sample_ids = row_sample_sheet["Sample_Name"]
        # Pick the column from sample_sheet that matches filtered_mynorm's column names
        # print("Checking which sample sheet column matches methylation matrix...")
        # print("sample_sheet[Sample_Name]:", sample_sheet["Sample_Name"].head())
        # print("filtered_mynorm columns:", list(filtered_mynorm.columns)[:5])
        row_mynorm = filtered_mynorm.loc[:, sample_ids]
        # print("row_mynorm shape:", row_mynorm.shape)
        # print("Any NaNs in row_mynorm?", row_mynorm.isna().any().any())
        # print(row_mynorm.iloc[:5, :5])
        
        # Selecting columns for the boxplot
        # data = pd.concat((row_mynorm.T, row_sample_sheet[column]), axis=1)
        # Ensure we join on matching index
        row_sample_sheet_indexed = row_sample_sheet.set_index("Sample_Name")

        # Transpose row_mynorm and ensure matching index name
        row_mynorm_T = row_mynorm.T
        row_mynorm_T.index.name = "Sample_Name"

        # Join grouping column from sample sheet
        data = row_mynorm_T.join(row_sample_sheet_indexed[[column]], how="inner")

        # print("[DEBUG] data.head()")
        # print(data.head())
        # print("Unique groups:", data[column].unique())

        # print("[DEBUG] data.head():")
        # print(data.head())
        # print("[DEBUG] data[column].unique():", data[column].unique())
        # print("[DEBUG] any NaNs in data before groupby?", data.isna().any().any())
        grouped_row = data.groupby(column).mean().T
        #grouped_row = grouped.loc[:, ids_to_plot]

        # Reset the index to include CpG as a column
        grouped_row_reset = grouped_row.reset_index(names="CpG")

        # Melt the grouped row into long format for plotly
        grouped_row_melted = grouped_row_reset.melt(
            id_vars="CpG", var_name=column, value_name="Mean beta value"
        )

        # print("grouped_row_melted preview:")
        # print(grouped_row_melted.head())
        # print("n rows:", len(grouped_row_melted))

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
    rows, cols = filtered_imp_mynorm.shape
    print(f"The filtered_imp_mynorm has {rows} rows and {cols} columns.")

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    print("INDEX NAME: ")
    print(sample_sheet.index.name)  
    sample_sheet[["Sentrix_ID", "Sentrix_Position"]] = sample_sheet[
        "Array_Position"
    ].str.split("_", expand=True)
    # print("1")
    # print(sample_sheet.columns)

    # compute the number of figures to generate and assign each
    # Sentrix_ID/Sentrix_Position to a specific subplot
    # sample_sheet["row_id"] = range(1, sample_sheet.index.size + 1)
    # sample_sheet["Plot_num"] = (sample_sheet["row_id"] - 1) // 10 + 1
    unique_ids = sample_sheet[[column]].drop_duplicates().reset_index(drop=True)
    unique_ids["Plot_num"] = (unique_ids.index // 10) + 1
    sample_sheet = sample_sheet.reset_index()
    sample_sheet = sample_sheet.merge(unique_ids, on=column, how="left")

    # print("2")
    # print(sample_sheet.columns)

    # TODO: pass filter_imp_mynorm and sample sheet to get_single_fig and filter there?
    # data = pd.concat((filtered_imp_mynorm.T, sample_sheet[["Plot_num", column]]), axis=1)
    #rows, cols = data.shape
    print(f"The data has {rows} rows and {cols} columns.")
    # print(data["Plot_num"].value_counts())

    # Create figure
    # beta_columns = filtered_imp_mynorm.columns 
    # grouped = data[beta_columns.tolist() + [column]].groupby(column).mean().T
    #grouped = data.groupby(column).mean().T

    for row_num in sample_sheet["Plot_num"].unique():
        fig = get_single_fig(
            column=column,
            filtered_mynorm = filtered_imp_mynorm,
            #grouped=grouped,
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
