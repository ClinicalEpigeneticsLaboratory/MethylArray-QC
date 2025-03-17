#!/usr/local/bin/python

import sys
import pandas as pd
import plotly as py
import plotly.express as px 

pd.options.plotting.backend = "plotly"

# TODO: reimplement using plain plotly and not plotly express - does not work!
# TypeError: plot() missing 1 required positional argument: 'kind'
def getFigUrl(path_to_imputed_mynorm: str, path_to_sample_sheet: str, column: str):

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
    return py.plot(fig, height = 600, width = 600, auto_open = False, filename = str("mean_beta_per_" + column))

def main():
    if len(sys.argv) != 3:
        print("Usage: python batch_effect.py <path_to_imputed_mynorm> <path_to_sample_sheet>")
        sys.exit(1)

    urls = []

    for col in ["Sentrix_ID", "Sentrix_Position"]:
        url = getFigUrl(path_to_imputed_mynorm = sys.argv[1], path_to_sample_sheet = sys.argv[2], column = col)
        print(url)
        urls.append(url)

if __name__ == "__main__":
    main()