#!/usr/local/bin/python

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.figure_factory as ff


# I cannot add customized hover to this type of plot, may require more work or impossible:
# https://stackoverflow.com/questions/62448872/plotly-how-to-modify-hovertemplate-of-a-histogram
def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python beta_distribution.py <path_to_imputed_mynorm> <n_cpgs_beta_distr>"
        )
        sys.exit(1)

    path_to_imputed_mynorm = Path(sys.argv[1])
    n_cpgs_beta_distr = int(sys.argv[2])

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    if "CpG" in imputed_mynorm.columns:
        imputed_mynorm.set_index("CpG", inplace=True)

    rng = np.random.RandomState(seed=123)

    # Get the list of randomly selected CpGs and filter data
    cpgs_to_plot = rng.choice(
        a=imputed_mynorm.index.to_list(), size=n_cpgs_beta_distr, replace=False
    )
    plot_data = imputed_mynorm.loc[cpgs_to_plot]
    plot_data = plot_data.T

    # Prepare figure
    plot_title = (
        f"Density plot of imputed data (randomly selected {n_cpgs_beta_distr} CpGs)"
    )

    fig = ff.create_distplot(
        plot_data.to_numpy(),
        group_labels=plot_data.index.to_list(),
        show_hist=False,
        show_rug=False,
        curve_type="kde",
    )
    fig.update_xaxes(range=[0, 1], title="Beta")
    fig.update_yaxes(title="Density")
    fig.update_layout(
        width=600,
        height=300,
        template="ggplot2",
        title_text=plot_title,
        showlegend=False,
    )
    fig.write_json(file="beta_distribution.json", pretty=True)


if __name__ == "__main__":
    main()
