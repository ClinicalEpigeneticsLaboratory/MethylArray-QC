#!/usr/local/bin/python

from decorators import update_and_export_plot
import sys
import plotly.graph_objects as go
import pandas as pd
import plotly.express as px

def getSingleFig(
    sample_sheet: pd.DataFrame,
    grouped: pd.DataFrame,
    row_num: int,
    column: str,
) -> go.Figure:
    ids_to_plot = list(
        sample_sheet.loc[sample_sheet["Plot_num"] == row_num, column]
    )

    # Check if we have valid Sentrix_IDs to plot
    if ids_to_plot:
        # Selecting columns for the boxplot
        grouped_row = grouped.loc[:, ids_to_plot]

        # Reset the index to include CpG as a column
        grouped_row_reset = grouped_row.reset_index(names="CpG")

        # Melt the grouped row into long format for plotly
        grouped_row_melted = grouped_row_reset.melt(
            id_vars="CpG", var_name=column, value_name="Mean beta value"
        )

        fig = px.box(grouped_row_melted, x=column, y="Mean beta value")
        fig.update_layout(boxgap=0.05)
        fig.update_xaxes(tickangle = 90)
        return fig
    else:
        print(f"Warning: No {column}s found for row {row_num}.")

def getAllFigs(
    path_to_imputed_mynorm: str, 
    path_to_sample_sheet: str, 
    column: str,
) -> None:
    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[["Sentrix_ID", "Sentrix_Position"]] = sample_sheet[
        "Array_Position"
    ].str.split("_", expand=True)

    # compute the number of figures to generate and assign each /Sentrix_Position to a specific subplot
    sample_sheet["row_id"] = range(1, sample_sheet.index.size + 1)
    sample_sheet["Plot_num"] = (sample_sheet["row_id"] - 1) // 10 + 1

    data = pd.concat((imputed_mynorm.T, sample_sheet[column]), axis=1)

    # Create figure
    grouped = data.groupby(column).mean().T

    for row_num in sample_sheet["Plot_num"].unique():
        fig = getSingleFig(
            column = column, 
            grouped = grouped, 
            row_num = row_num,
            sample_sheet = sample_sheet,
        )

        if fig is not None:
            @update_and_export_plot(f"{row_num}.json")
            def exportFig():
                return fig
            exportFig()


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python batch_effect.py <path_to_imputed_mynorm> <path_to_sample_sheet> <column>"
        )
        sys.exit(1)

    imputed_mynorm_path = sys.argv[1]
    sample_sheet_path = sys.argv[2]
    col = str(sys.argv[3])

    getAllFigs(
        path_to_imputed_mynorm=imputed_mynorm_path,
        path_to_sample_sheet=sample_sheet_path,
        column=col,
    )


if __name__ == "__main__":
    main()
