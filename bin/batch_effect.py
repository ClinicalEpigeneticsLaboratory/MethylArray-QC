#!/usr/local/bin/python

import pandas as pd
from pathlib import Path
import plotly.express as px 
import sys

def getFigJson(path_to_imputed_mynorm: str, path_to_sample_sheet: str, column: str):

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)
    
    # compute the number of figures to generate and assign each /Sentrix_Position to a specific subplot
    sample_sheet["row_id"] = range(1, sample_sheet.index.size + 1)
    sample_sheet["Plot_num"] = (sample_sheet["row_id"] -1) // 10 + 1

    data = pd.concat((imputed_mynorm.T, sample_sheet[column]), axis=1)

    # Create figure
    grouped = data.groupby(column).mean().T

    # the logic for subplot generation if there are more than 1 plots to generate
    plot_rows = sample_sheet["Plot_num"].nunique()
    plot_height = 600*plot_rows

    for row_num in sample_sheet["Plot_num"].unique():

        ids_to_plot = list(sample_sheet.loc[sample_sheet['Plot_num'] == row_num, column])

        # Check if we have valid Sentrix_IDs to plot
        if ids_to_plot:
            # Selecting columns for the boxplot
            grouped_row = grouped.loc[:, ids_to_plot]

            # Reset the index to include CpG as a column
            grouped_row_reset = grouped_row.reset_index(names = "CpG")

            # Melt the grouped row into long format for plotly
            grouped_row_melted = grouped_row_reset.melt(id_vars="CpG", var_name=column, value_name="Mean beta value")

            fig = px.box(grouped_row_melted, x = column, y = "Mean beta value")
            fig.update_layout(width = 600, height = plot_height, template = "ggplot2")
            fig.write_json(file = f"Mean_beta_per_{column}/{row_num}.json", pretty = True)
        else:
            print(f"Warning: No {column}s found for row {row_num}.")

def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_effect.py <path_to_imputed_mynorm> <path_to_sample_sheet>")
        sys.exit(1)

    for col in ["Sentrix_ID", "Sentrix_Position"]:

        # Create the directory
        col_out_dir_path = Path(f"./Mean_beta_per_{col}")
        col_out_dir_path.mkdir(exist_ok = True)
        getFigJson(path_to_imputed_mynorm = sys.argv[1], path_to_sample_sheet = sys.argv[2], column = str(col))

if __name__ == "__main__":
    main()