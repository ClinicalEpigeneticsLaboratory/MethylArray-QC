#!/usr/local/bin/python

import sys
import pandas as pd
import plotly.express as px 
from plotly.offline import plot, get_plotlyjs

# TODO: reimplement using plain plotly and not plotly express - does not work!
# TypeError: plot() missing 1 required positional argument: 'kind'

# or try to use: https://plotly.com/python/interactive-html-export/

# Solution that seems to work for now (to verify):
# https://medium.com/@simovic.peter/learn-how-to-create-plotly-powered-reporting-supercharged-with-javascript-and-css-bede89d38d5e
def getFigDiv(path_to_imputed_mynorm: str, path_to_sample_sheet: str, column: str):

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    imputed_mynorm.set_index("CpG", inplace=True)

    sample_sheet = pd.read_csv(path_to_sample_sheet, index_col=0)
    sample_sheet[['Sentrix_ID','Sentrix_Position']] = sample_sheet['Array_Position'].str.split('_',expand=True)

    data = pd.concat((imputed_mynorm.T, sample_sheet[column]), axis=1)

    # Create figure
    grouped = data.groupby(column).mean().T

    fig = px.box(grouped)
    fig.update_layout(width=600, height=600)
    return plot(fig, output_type='div', include_plotlyjs=False)

def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_effect.py <path_to_imputed_mynorm> <path_to_sample_sheet>")
        sys.exit(1)

    div_res = ""

    for col in ["Sentrix_ID", "Sentrix_Position"]:
        div = getFigDiv(path_to_imputed_mynorm = sys.argv[1], path_to_sample_sheet = sys.argv[2], column = col)
        div_res = div_res + div

    print(div_res)

if __name__ == "__main__":
    main()