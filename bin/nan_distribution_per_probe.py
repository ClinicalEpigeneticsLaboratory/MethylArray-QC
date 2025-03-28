#!/usr/local/bin/python

import sys
import plotly.graph_objects as go
import pandas as pd

def main():
    if len(sys.argv) != 3:
        print("Usage: python nan_distribution_per_probe.py <path_to_raw_mynorm> <top_nan_per_probe_cpgs>")
        sys.exit(1)

    path_to_raw_mynorm = sys.argv[1]
    top_nan_per_probe_cpgs = int(sys.argv[2])

    raw_mynorm = pd.read_parquet(path_to_raw_mynorm)
    raw_mynorm.set_index("CpG", inplace = True)

    if top_nan_per_probe_cpgs > len(raw_mynorm.index):
        raise Exception("top_nan_per_probe_cpgs parameter cannot be larger than the number of rows in raw_mynorm!")

    top_n_nan_probes = raw_mynorm.isna().sum(axis=1).sort_values(ascending=False).head(top_nan_per_probe_cpgs).index
    
    raw_mynorm_top_n_nan = raw_mynorm.loc[top_n_nan_probes]

    # Convert the data into a binary matrix where 1 represents NaN, 0 represents non-NaN
    raw_mynorm_nan = raw_mynorm_top_n_nan.isna().astype(int)

    fig = go.Figure(data=go.Heatmap(
        z=raw_mynorm_nan,
        x = raw_mynorm_nan.columns,
        y = raw_mynorm_nan.index,
        colorscale = [[0, 'rgb(0,0,0)'], [1, 'rgb(255,255,0)']],
        zmin=0,
        zmax=1,
        colorbar=dict(title="NaN Distribution<br>(0 - no NaN, 1 - NaN)")
    ))

    fig.update_layout(
        title=f'NaN distribution across {top_nan_per_probe_cpgs} CpGs with highest NaN count',
        xaxis_title='Sample_Name',
        yaxis_title='CpG'
    )

    fig.update_xaxes(showticklabels = False)
    fig.update_yaxes(showticklabels = False)
    fig.update_layout(width = 600, height = 600, template = "ggplot2")
    fig.write_json(file = "nan_distribution_per_probe.json", pretty = True)

if __name__ == "__main__":
    main()
