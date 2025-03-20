#!/usr/local/bin/python

import pandas as pd
from pathlib import Path
import plotly.figure_factory as ff
import sys
import random

# an idea: do we want a random seed to be provided by the user as an parameter?
random.seed(123)

def main():
    if len(sys.argv) != 3:
        print("Usage: python beta_distribution.py <path_to_imputed_mynorm> <n_cpgs_beta_distr>")
        sys.exit(1)

    path_to_imputed_mynorm = Path(sys.argv[1])
    n_cpgs_beta_distr = int(sys.argv[2])

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    if "CpG" in imputed_mynorm.columns:
        imputed_mynorm.set_index("CpG", inplace = True)

    # Get the list of randomly selected CpGs and filter data
    cpgs_to_plot = random.sample(imputed_mynorm.index.to_list(), n_cpgs_beta_distr)
    plot_data = imputed_mynorm.filter(items = cpgs_to_plot, axis = 0)
    plot_data = plot_data.T

    # Prepare figure
    plot_title = f'Density plot of imputed data (randomly selected {n_cpgs_beta_distr} CpGs)'
    
    fig = ff.create_distplot(plot_data.to_numpy(), group_labels = plot_data.index.to_list(), show_hist = False, show_rug = False, curve_type = "kde")
    fig.update_xaxes(range=[0, 1], title = "Beta")
    fig.update_yaxes(title = "Density")
    fig.update_layout(width = 600, height = 300, template = "ggplot2", title_text = plot_title, showlegend = False)
    fig.write_html(file = "beta_distribution.html")

if __name__ == "__main__":
    main()