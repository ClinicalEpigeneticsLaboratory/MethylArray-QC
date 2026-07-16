#!/usr/local/bin/python

"""
A module generating a heatmap presenting the distribution of
missing values across probes and samples
"""

import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from decorators import update_and_export_plot
from i18n import t


@update_and_export_plot(json_path="nan_distribution_per_probe.json")
def get_nan_distr_per_probe_fig(
    plot_data: pd.DataFrame, nan_per_probe_n_cpgs: int, language: str = "en"
) -> go.Figure:
    """A function generating a heatmap presenting the distribution of
missing values across probes and samples

    Args:
        plot_data (pd.DataFrame): data used to generate a plot
        nan_per_probe_n_cpgs (int): number of randomly selected CpG sites\
            to be plotted (parameter provided by the user)
        language (str): report language ("en"/"pl") for the plot title

    Returns:
        go.Figure: a heatmap showing the distribution of missing values across probes and samples
    """
    hovertext = []
    for yi, yy in enumerate(plot_data.index):
        hovertext.append([])
        for xi, xx in enumerate(plot_data.columns):
            nan_label = "yes" if plot_data.iloc[yi, xi] == 1 else "no"
            hovertext[-1].append(
                f"Sample_Name: {xx}<br>CpG: {yy}<br>Is NaN? {nan_label}"
            )

    fig = go.Figure(
        data=go.Heatmap(
            z=plot_data,
            x=plot_data.columns,
            y=plot_data.index,
            colorscale=[[0, "rgb(0,0,0)"], [1, "rgb(135,206,250)"]],
            zmin=0,
            zmax=1,
            hoverinfo="text",
            text=hovertext,
            colorbar={
                "title": None,
                "tickvals": [0, 1],
                "ticktext": ["No NaN", "NaN"],
                "tickmode": "array",
                "ticks": "outside",
                "lenmode": "fraction",  # Use fraction instead of pixels
                "len": 0.8,  # Shorter color bar (30% of plot height)
                "ticklen": 10,
                "tickwidth": 2,
                "tickangle": 0,
            },
        )
    )

    fig.update_layout(
        title=t("plot.nan_probe.title", language, n=nan_per_probe_n_cpgs),
        # xaxis/yaxis titles are the source column names (Sample_Name, CpG), kept
        # as-is - they are data identifiers, not UI chrome (see plan D2/D6).
        xaxis_title="Sample_Name",
        yaxis_title="CpG",
    )

    fig.update_traces(coloraxis=None)

    fig.update_yaxes(showticklabels=False, visible=False)
    return fig


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python nan_distribution_per_probe.py \
                <path_to_raw_mynorm: str> <top_nan_per_probe_cpgs: int> \
                <report_language: en|pl>"
        )
        sys.exit(1)

    path_to_raw_mynorm = sys.argv[1]
    nan_per_probe_n_cpgs = int(sys.argv[2])
    language = sys.argv[3]

    raw_mynorm = pd.read_parquet(path_to_raw_mynorm)
    raw_mynorm.set_index("CpG", inplace=True)

    if nan_per_probe_n_cpgs > len(raw_mynorm.index):
        raise ValueError(
            "nan_per_probe_n_cpgs parameter cannot be larger than the number of rows in raw_mynorm!"
        )

    rng = np.random.RandomState(seed=123)

    # Get the list of randomly selected CpGs and filter data
    cpgs_to_plot = rng.choice(
        a=raw_mynorm.index.to_list(), size=nan_per_probe_n_cpgs, replace=False
    )

    raw_mynorm_n_nan = raw_mynorm.loc[cpgs_to_plot]

    # Convert the data into a binary matrix where 1 represents NaN, 0 represents non-NaN
    plot_data = raw_mynorm_n_nan.isna().astype(int)

    get_nan_distr_per_probe_fig(
        plot_data=plot_data, nan_per_probe_n_cpgs=nan_per_probe_n_cpgs, language=language
    )


if __name__ == "__main__":
    main()
