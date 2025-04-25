#!/usr/local/bin/python

"""
A module used for the generation of epigenetic age plots
"""

import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plot_export_utils import export_decorated_fig_with_custom_name
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import median_absolute_error


def get_med_ae(x: list, y: list) -> float:
    """A function calculating median absolute error for epigenetic age estimation

    Args:
        x (list): chronological age of subjects
        y (list): epigenetic age of subjects

    Returns:
        float: median absolute error
    """
    model = LinearRegression()
    x = x.reshape(-1, 1)
    model.fit(x, y)
    y_pred = model.predict(x)
    medae = median_absolute_error(y, y_pred)
    return medae


def add_med_ae_to_trendline_hover(hovertemplate: str, medae: float) -> str:
    """A helper function adding median absolute error to \
        trendline hover template in regression plot

    Args:
        hovertemplate (str): current hovertemplate
        medae (float): median absolute error

    Returns:
        str: updated hovertemplate
    """
    return f"{hovertemplate}<br>Median Absolute Error: {medae:.2f}"


def get_eaa_boxplot(data: pd.DataFrame, epi_clock: str) -> go.Figure:
    """A function generating epigenetic age acceleration boxplot

    Args:
        data (pd.DataFrame): plot data used to generate boxplots
        epi_clock (str): the name of currently processed epigenetic clock

    Returns:
        go.Figure: Epigenetic age acceleration boxplot figure
    """
    kruskal_res = stats.kruskal(
        *[
            group[f"Age_Acceleration_{epi_clock}"].values
            for name, group in data.groupby("Sample_Group")
        ]
    )
    fig = px.box(
        data,
        x="Sample_Group",
        y=f"Age_Acceleration_{epi_clock}",
        color="Sample_Group",
        points="all",
        hover_data=data.columns.to_list(),
    )
    fig.update_layout(
        yaxis={"title": f"{epi_clock}_Accel"},
        title={
            "text": f"Kruskal-Wallis p = {kruskal_res.pvalue: .2f}",
            "font": {"size": 20},
            "x": 0.15,
        },
    )

    if fig is not None:
        export_decorated_fig_with_custom_name(
            fig=fig, json_path=f"Epi_Age_Accel_{epi_clock}.json", showlegend=False
        )


def get_epi_vs_chron_age_regr_plot(
    data: pd.DataFrame, epi_clock: str, hover_cols: list
) -> None:
    """A function generating regression plot comparing \
        chronological and epigenetic age for specific clock \
        (generally and per group)

    Args:
        data (pd.DataFrame): data used to generate a plot
        epi_clock (str): the name of currently processed epigenetic clock
        hover_cols (list): the list of columns to be presented on hovering over a point
    """

    overall_medae = get_med_ae(x=data["Age"].values, y=data[f"mAge_{epi_clock}"].values)

    if "Sample_Group" in data:
        fig = px.scatter(
            data,
            x="Age",
            y=f"mAge_{epi_clock}",
            color="Sample_Group",
            trendline="ols",
            hover_data=hover_cols,
        )

        # Overall trendline for all data points
        overall_trendline = px.scatter(
            data,
            x="Age",
            y=f"mAge_{epi_clock}",
            trendline="ols",
            trendline_scope="overall",
            trendline_color_override="black",
        )

        trendline_trace = overall_trendline.data[1]

        # Update the hovertemplate for the overall trendline
        trendline_trace.update(
            hovertemplate=add_med_ae_to_trendline_hover(
                hovertemplate=trendline_trace.hovertemplate, medae=overall_medae
            )
        )

        # Add the overall trendline trace to the figure
        fig.add_trace(trendline_trace)

        for group in data["Sample_Group"].unique():
            group_data = data[data["Sample_Group"] == group]

            group_medae = get_med_ae(
                x=group_data["Age"].values, y=group_data[f"mAge_{epi_clock}"].values
            )

            # Identify the trace for this group
            group_trace_index = [
                i for i, trace in enumerate(fig.data) if trace.name == group
            ][1]
            group_trace = fig.data[group_trace_index]

            # Update the hovertemplate for this group's trace
            group_trace.hovertemplate = add_med_ae_to_trendline_hover(
                hovertemplate=group_trace.hovertemplate, medae=group_medae
            )
    else:
        fig = px.scatter(
            data, x="Age", y=f"mAge_{epi_clock}", trendline="ols", hover_data=hover_cols
        )

        trendline_trace = fig.data[1]  # The trendline trace is usually the second trace

        trendline_trace.hovertemplate = add_med_ae_to_trendline_hover(
            hovertemplate=trendline_trace.hovertemplate, medae=overall_medae
        )

    fig.update_layout(
        yaxis={"title": epi_clock},
        legend={
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "orientation": "h",
        },
    )

    if fig is not None:
        export_decorated_fig_with_custom_name(
            fig=fig,
            json_path=f"Regr_Age_vs_Epi_Age_{epi_clock}.json",
        )


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python epigenetic_age_plots.py <path_to_epi_age_res: str> \
                <path_to_sample_sheet: str> <epi_clock: str>"
        )
        sys.exit(1)

    path_to_epi_age_res = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    epi_clock = sys.argv[3]

    # Load data
    epi_age_res = pd.read_parquet(path_to_epi_age_res)
    sample_sheet = pd.read_csv(path_to_sample_sheet)

    epi_clock_res = epi_age_res[
        ["Sample", f"mAge_{epi_clock}", f"Age_Acceleration_{epi_clock}"]
    ]
    epi_clock_res.rename(columns={"Sample": "Sample_Name"}, inplace=True)
    data = epi_clock_res.merge(sample_sheet, on="Sample_Name")

    get_epi_vs_chron_age_regr_plot(
        data=data, epi_clock=epi_clock, hover_cols=sample_sheet.columns.to_list()
    )

    if "Sample_Group" in sample_sheet:
        get_eaa_boxplot(data=data, epi_clock=epi_clock)


if __name__ == "__main__":
    main()
