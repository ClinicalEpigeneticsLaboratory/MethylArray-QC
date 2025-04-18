#!/usr/local/bin/python

from decorators import update_and_export_plot

import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

@update_and_export_plot(json_path = "nan_distribution_per_probe.json")
def getNanDistrPerProbeFig(plot_data: pd.DataFrame, nan_per_probe_n_cpgs: int) -> go.Figure:
    
    hovertext = list()
    for yi, yy in enumerate(plot_data.index):
        hovertext.append(list())
        for xi, xx in enumerate(plot_data.columns):
            nan_label = 'yes' if plot_data.iloc[yi, xi] == 1 else 'no'
            hovertext[-1].append(f'Sample_Name: {xx}<br>CpG: {yy}<br>Is NaN? {nan_label}')
    
    fig = go.Figure(
        data=go.Heatmap(
            z=plot_data,
            x=plot_data.columns,
            y=plot_data.index,
            colorscale=[[0, "rgb(0,0,0)"], [1, "rgb(135,206,250)"]],
            zmin=0,
            zmax=1,
            hoverinfo = "text",
            text = hovertext,
            colorbar=dict(
                title = None,
                tickvals=[0, 1],
                ticktext=["No NaN", "NaN"],
                tickmode="array",
                ticks="outside",
                lenmode="fraction",  # Use fraction instead of pixels
                len=0.8,              # Shorter color bar (30% of plot height)
                ticklen=10,
                tickwidth=2,
                tickangle=0,
            ),
        )
    )

    fig.update_layout(
        title=f"NaN distribution across<br>{nan_per_probe_n_cpgs} randomly selected CpGs",
        xaxis_title="Sample_Name",
        yaxis_title="CpG",
    )

    fig.update_traces(coloraxis=None)

    fig.update_yaxes(showticklabels=False, visible=False)
    return fig

def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python nan_distribution_per_probe.py <path_to_raw_mynorm> <top_nan_per_probe_cpgs>"
        )
        sys.exit(1)

    path_to_raw_mynorm = sys.argv[1]
    nan_per_probe_n_cpgs = int(sys.argv[2])

    raw_mynorm = pd.read_parquet(path_to_raw_mynorm)
    raw_mynorm.set_index("CpG", inplace=True)

    if nan_per_probe_n_cpgs > len(raw_mynorm.index):
        raise Exception(
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

    getNanDistrPerProbeFig(plot_data = plot_data, nan_per_probe_n_cpgs = nan_per_probe_n_cpgs)


if __name__ == "__main__":
    main()
