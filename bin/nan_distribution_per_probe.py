#!/usr/local/bin/python

import numpy as np
import sys
import plotly.graph_objects as go
import pandas as pd


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
    raw_mynorm_nan = raw_mynorm_n_nan.isna().astype(int)

    fig = go.Figure(
        data=go.Heatmap(
            z=raw_mynorm_nan,
            x=raw_mynorm_nan.columns,
            y=raw_mynorm_nan.index,
            colorscale=[[0, "rgb(0,0,0)"], [1, "rgb(135,206,250)"]],
            zmin=0,
            zmax=1,
            colorbar=dict(
                title="NaN Distribution",
                tickvals=[0, 1],  
                ticktext=['No NaN', 'NaN'],  
                tickmode='array', 
                ticks='outside',  
                lenmode="pixels",  
                ticklen=10,  
                tickwidth=2,  
                tickangle=0  
            )
        )
    )

    fig.update_layout(
        title=f"NaN distribution across {nan_per_probe_n_cpgs} randomly selected CpGs",
        xaxis_title="Sample_Name",
        yaxis_title="CpG"
    )

    fig.update_traces(coloraxis=None)

    fig.update_xaxes(showticklabels=False, visible = False)
    fig.update_yaxes(showticklabels=False, visible = False)
    fig.update_layout(width=600, height=600, template="ggplot2")
    fig.write_json(file="nan_distribution_per_probe.json", pretty=True)


if __name__ == "__main__":
    main()
