#!/usr/local/bin/python

import sys
import pandas as pd
import plotly.express as px
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.metrics import median_absolute_error


def getMedAE(x: list, y: list) -> float:
    model = LinearRegression()
    x = x.reshape(-1, 1)
    model.fit(x, y)
    y_pred = model.predict(x)
    medae = median_absolute_error(y, y_pred)
    return medae


def addMedAEToTrendlineHover(hovertemplate: str, medae: float) -> str:
    return f"{hovertemplate}<br>Median Absolute Error: {medae:.2f}"


def getEAABoxplot(data: pd.DataFrame, epi_clock: str):
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
        title=f"Kruskal-Wallis p = {kruskal_res.pvalue: .2f}",
    )
    fig.update_layout(
        width=600,
        height=600,
        template="ggplot2",
        yaxis={"title": epi_clock},
        legend={"title": None},
    )
    fig.write_json(file=f"Epi_Age_Accel_{epi_clock}.json", pretty=True)


def getEpivsChronAgeRegrPlot(
    data: pd.DataFrame, epi_clock: str, hover_cols: list
) -> None:

    overall_medae = getMedAE(x=data["Age"].values, y=data[f"mAge_{epi_clock}"].values)

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
            hovertemplate=addMedAEToTrendlineHover(
                hovertemplate=trendline_trace.hovertemplate, medae=overall_medae
            )
        )

        # Add the overall trendline trace to the figure
        fig.add_trace(trendline_trace)

        for group in data["Sample_Group"].unique():
            group_data = data[data["Sample_Group"] == group]

            group_medae = getMedAE(
                x=group_data["Age"].values, y=group_data[f"mAge_{epi_clock}"].values
            )

            # Identify the trace for this group
            group_trace_index = [
                i for i, trace in enumerate(fig.data) if trace.name == group
            ][1]
            group_trace = fig.data[group_trace_index]

            # Update the hovertemplate for this group's trace
            group_trace.hovertemplate = addMedAEToTrendlineHover(
                hovertemplate=group_trace.hovertemplate, medae=group_medae
            )
    else:
        fig = px.scatter(
            data, x="Age", y=f"mAge_{epi_clock}", trendline="ols", hover_data=hover_cols
        )

        trendline_trace = fig.data[1]  # The trendline trace is usually the second trace

        trendline_trace.hovertemplate = addMedAEToTrendlineHover(
            hovertemplate=trendline_trace.hovertemplate, medae=overall_medae
        )

    fig.update_layout(
        width=600,
        height=600,
        template="ggplot2",
        yaxis={"title": epi_clock},
        legend={"title": None},
    )
    fig.write_json(file=f"Regr_Age_vs_Epi_Age_{epi_clock}.json", pretty=True)

def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python epigenetic_age_plots.py <path_to_epi_age_res> <path_to_sample_sheet> <epi_clock>"
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

    getEpivsChronAgeRegrPlot(
        data=data, epi_clock=epi_clock, hover_cols=sample_sheet.columns.to_list()
    )

    if "Sample_Group" in sample_sheet:
        getEAABoxplot(data=data, epi_clock=epi_clock)


if __name__ == "__main__":
    main()
