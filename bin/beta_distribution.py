#!/usr/local/bin/python

"""
A module generating beta distribution plot
"""

import sys
from pathlib import Path
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.figure_factory as ff
# from scipy.stats import gaussian_kde
from decorators import update_and_export_plot
from i18n import t


@update_and_export_plot(
    json_path="beta_distribution.json", height=325, showlegend=False
)
def get_beta_distr_plot(n_cpgs_beta_distr: int, plot_data: pd.DataFrame, language: str = "en") -> ff:
    """A function generating beta distribution plot

    Args:
        n_cpgs_beta_distr (int): number of randomly selected CpG sites used to generate a plot \
            (parameter passed by the user)
        plot_data (pd.DataFrame): data neccessary to generate a plot
        language (str): report language ("en"/"pl") for the axis/title labels

    Returns:
        ff: beta distribution plot
    """
    # Prepare figure
    plot_title = t("plot.beta.title", language, n=n_cpgs_beta_distr)

    fig = ff.create_distplot(
        plot_data.to_numpy(),
        group_labels=plot_data.index.to_list(),
        show_hist=False,
        show_rug=False,
        curve_type="kde",
    )
    fig.update_xaxes(range=[0, 1], title=t("plot.beta.xaxis", language))
    fig.update_yaxes(title=t("plot.beta.yaxis", language))
    fig.update_layout(title_text=plot_title, margin_t=125)

    return fig


# I cannot add customized hover to this type of plot, may require more work or impossible:
# https://stackoverflow.com/questions/62448872/plotly-how-to-modify-hovertemplate-of-a-histogram
def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python beta_distribution.py <path_to_imputed_mynorm: str> \
                <n_cpgs_beta_distr: int> <report_language: en|pl>"
        )
        sys.exit(1)

    path_to_imputed_mynorm = Path(sys.argv[1])
    n_rand_cpgs = int(sys.argv[2])
    language = sys.argv[3]

    # Load data
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)
    if "CpG" in imputed_mynorm.columns:
        imputed_mynorm.set_index("CpG", inplace=True)

    rng = np.random.RandomState(seed=123)

    # Get the list of randomly selected CpGs and filter data
    cpgs_to_plot = rng.choice(
        a=imputed_mynorm.index.to_list(), size=n_rand_cpgs, replace=False
    )

    random_cpgs_list = cpgs_to_plot.tolist()

    with open("random_cpgs_to_plot.json", "w", encoding="utf-8") as f:
        json.dump(random_cpgs_list, f, indent=2)

    plot_data = imputed_mynorm.loc[cpgs_to_plot]
    plot_data = plot_data.T

    get_beta_distr_plot(n_cpgs_beta_distr=n_rand_cpgs, plot_data=plot_data, language=language)


if __name__ == "__main__":
    main()
