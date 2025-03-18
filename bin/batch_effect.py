#!/usr/local/bin/python

import pandas as pd
import plotly.express as px 
import plotly.io as pio
import sys

pio.renderers.default = "browser"

# Function generating figure HTML to embed in HTML report:
# https://plotly.com/python/v3/html-reports/
#
# Managed to generate figure HTML - we can try to embed them with iframe in the report
def getFigHtml(path_to_imputed_mynorm: str, path_to_sample_sheet: str, column: str):

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)

    data = pd.concat((imputed_mynorm.T, sample_sheet[column]), axis=1)

    # Create figure
    grouped = data.groupby(column).mean().T

    fig = px.box(grouped, labels={
                     "value": "Mean beta value"
                 })
    fig.update_layout(width=600, height=600)
    fig.write_html(file = str("mean_meth_per_" + column + ".html"))

def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_effect.py <path_to_imputed_mynorm> <path_to_sample_sheet>")
        sys.exit(1)

    for col in ["Sentrix_ID", "Sentrix_Position"]:
        getFigHtml(path_to_imputed_mynorm = sys.argv[1], path_to_sample_sheet = sys.argv[2], column = str(col))

if __name__ == "__main__":
    main()