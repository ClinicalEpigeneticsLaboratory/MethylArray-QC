#!/usr/local/bin/python

import pandas as pd
import plotly.express as px 
import sys
from plotly.subplots import make_subplots

import pandas as pd
import plotly.express as px 
import sys
from plotly.subplots import make_subplots

# TODO: think how to solve - this approach is very memory inefficient and can fail for large number of Sentrix_IDs! Tested on 67 Sentrix_IDs (result: failed with MemoryError)
def getFigJson(path_to_imputed_mynorm: str, path_to_sample_sheet: str, column: str):

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)
    
    # compute the number of figures to generate and assign each Sentrix_ID to a specific subplot
    sample_sheet["row_id"] = range(1, sample_sheet.index.size + 1)
    sample_sheet["Sentrix_ID_subplot_num"] = (sample_sheet["row_id"] -1) // 10 + 1

    data = pd.concat((imputed_mynorm.T, sample_sheet[column]), axis=1)

    # Create figure
    grouped = data.groupby(column).mean().T

    # the logic for subplot generation if there are more than 1 plots to generate
    if column == "Sentrix_ID" and sample_sheet["Sentrix_ID_subplot_num"].nunique() > 1:

        plot_rows = sample_sheet["Sentrix_ID_subplot_num"].nunique()

        fig = make_subplots(rows = plot_rows, cols = 1)
        plot_height = 600*plot_rows

        for row_num in sample_sheet["Sentrix_ID_subplot_num"].unique():

            sentrix_ids_to_plot = list(sample_sheet.loc[sample_sheet['Sentrix_ID_subplot_num'] == row_num, 'Sentrix_ID'])

            # Check if we have valid Sentrix_IDs to plot
            if sentrix_ids_to_plot:
                # Selecting columns for the boxplot
                grouped_row = grouped.loc[:, sentrix_ids_to_plot]
                
                # extracting the trace from px.box
                box_fig = px.box(grouped_row, labels={"value": "Mean beta value"})
                
                # Append the first trace (boxplot trace) to the subplot
                fig.add_trace(
                    box_fig.data[0],  # Access the first trace
                    row=row_num, 
                    col=1
                )
            else:
                print(f"Warning: No Sentrix_IDs found for row {row_num}.")

    else:
        plot_height = 600
        fig = px.box(grouped, labels={"value": "Mean beta value"})

    fig.update_layout(width = 600, height = plot_height, template = "ggplot2")
    fig.write_json(file = str("mean_meth_per_" + column + ".json"))

def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_effect.py <path_to_imputed_mynorm> <path_to_sample_sheet>")
        sys.exit(1)

    for col in ["Sentrix_ID", "Sentrix_Position"]:
        getFigJson(path_to_imputed_mynorm = sys.argv[1], path_to_sample_sheet = sys.argv[2], column = str(col))

if __name__ == "__main__":
    main()