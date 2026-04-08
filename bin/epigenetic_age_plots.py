#!/usr/local/bin/python

"""
A module used for the generation of epigenetic age plots
"""

import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plot_export_utils import export_decorated_fig_with_custom_name
import pingouin as pg
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
        str: updated hovertemplate with median absolute error inserted
             before the <extra> tag so it renders in the main hover box
    """
    medae_text = f"<br>Median Absolute Error: {medae:.2f}"
    if "<extra>" in hovertemplate:
        return hovertemplate.replace("<extra>", f"{medae_text}<extra>", 1)
    return f"{hovertemplate}{medae_text}"

def get_pairwise_comp_res(data: pd.DataFrame, epi_clock: str) -> pd.DataFrame:
    """A function computing pairwise post-hoc test (U-Mann-Whitney, 
    FDR Benjamini-Hochberg correction)

    Args:
        data (pd.DataFrame): plot data used to generate epigenetic age acceleration 
                            boxplots
        epi_clock (str): the name of currently processed epigenetic clock

    Returns:
        pd.DataFrame: Results of the pairwise comparisons
    """
    posthoc = pg.pairwise_tests(
        dv=f"Age_Acceleration_{epi_clock}",
        between="Sample_Group",
        effsize="hedges",
        data=data,
        parametric=False,
        padjust="fdr_bh"
    )

    return pd.DataFrame(
        data = {
            'Group A': posthoc["A"],
            'Group B': posthoc["B"],
            'Post-hoc test': "U-Mann-Whitney",
            'p-value (uncorrected)': posthoc["p-unc"].round(3),
            'Multiple correction method': 'FDR Benjamini-Hochberg',
            'p-value (corrected)': posthoc["p-corr"].round(3),
            'Hedges g': posthoc["hedges"].round(3)
        },
    )

def get_eaa_boxplot(data: pd.DataFrame, epi_clock: str, posthoc_res: pd.DataFrame = None) -> go.Figure:
    """A function generating epigenetic age acceleration boxplot

    Args:
        data (pd.DataFrame): plot data used to generate boxplots
        epi_clock (str): the name of currently processed epigenetic clock
        posthoc_res (pd.DataFrame): data frame with results of post-hoc pairwise test, used to plot the results (default: None)
        
    Returns:
        go.Figure: Epigenetic age acceleration boxplot figure
    """

    kw_res = pg.kruskal(
        data=data,
        dv=f"Age_Acceleration_{epi_clock}",  
        between="Sample_Group"               
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
            "text": f"Kruskal-Wallis p = {kw_res["p-unc"].iloc[0]: .2f}",
            "x": 0.15,
        },
    )

    if fig is not None:
        export_decorated_fig_with_custom_name(
            fig=fig, json_path=f"Epi_Age_Accel_{epi_clock}.json", showlegend=False
        )

def get_eaa_res(
    data: pd.DataFrame, epi_clock: str
) -> None:
    """A function generating epigenetic age acceleration results

    Args:
        data (pd.DataFrame): plot data used to generate boxplots
        epi_clock (str): the name of currently processed epigenetic clock
        
    Returns: None
    """

    # compute post-hoc tests if there are >= 3 groups
    if data["Sample_Group"].nunique() >= 3:
        pairwise_res = get_pairwise_comp_res(data=data, epi_clock=epi_clock)
        pairwise_res.to_json(f"Epi_Age_Accel_{epi_clock}_post_hoc_res.json", orient="records", indent=2)
    get_eaa_boxplot(data=data, epi_clock=epi_clock, posthoc_res=None)

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

    valid_hover_cols = [c for c in hover_cols if c in data.columns]

    # NOTE: Do NOT pass hover_data to px.scatter when trendline="ols".
    # Plotly 5.24.1 generates broken customdata/hovertemplate when both
    # are used together, silently killing scatter marker hover.
    # Use hovertext (pre-built strings) instead of customdata/hovertemplate.

    def _build_hover_texts(df: pd.DataFrame) -> list:
        """Build hover text strings for each row in the DataFrame."""
        texts = []
        for _, row in df.iterrows():
            parts = [f"Age: {row['Age']}", f"mAge_{epi_clock}: {row[f'mAge_{epi_clock}']:.2f}"]
            for col in valid_hover_cols:
                val = row[col]
                if isinstance(val, float):
                    parts.append(f"{col}: {val:.2f}")
                else:
                    parts.append(f"{col}: {val}")
            texts.append("<br>".join(parts))
        return texts

    if "Sample_Group" in data:
        fig = px.scatter(
            data,
            x="Age",
            y=f"mAge_{epi_clock}",
            color="Sample_Group",
            trendline="ols",
        )

        # Set hover text on scatter (marker) traces using hovertext property
        for trace in fig.data:
            if getattr(trace, "mode", None) != "markers":
                continue
            group_df = data[data["Sample_Group"] == trace.name]
            trace.hovertext = _build_hover_texts(group_df)
            trace.hoverinfo = "text"

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

            # Identify the trendline trace for this group
            group_trace_index = [
                i for i, trace in enumerate(fig.data) if trace.name == group and getattr(trace, "mode", "") == "lines"
            ][0]
            group_trace = fig.data[group_trace_index]

            # Update the hovertemplate for this group's trendline trace
            group_trace.hovertemplate = add_med_ae_to_trendline_hover(
                hovertemplate=group_trace.hovertemplate, medae=group_medae
            )
    else:
        fig = px.scatter(
            data, x="Age", y=f"mAge_{epi_clock}", trendline="ols",
        )

        # Set hover text on the scatter (marker) trace
        marker_trace = next(t for t in fig.data if getattr(t, "mode", None) == "markers")
        marker_trace.hovertext = _build_hover_texts(data)
        marker_trace.hoverinfo = "text"

        trendline_trace = next(t for t in fig.data if getattr(t, "mode", "") == "lines")

        trendline_trace.hovertemplate = add_med_ae_to_trendline_hover(
            hovertemplate=trendline_trace.hovertemplate, medae=overall_medae
        )

    fig.update_layout(
        yaxis={"title": epi_clock},
        # legend={
        #     "yanchor": "bottom",
        #     "y": 1.02,
        #     "xanchor": "left",
        #     "x": 0,
        #     "orientation": "h",
        # },
    )

    if fig is not None:
        export_decorated_fig_with_custom_name(
            fig=fig,
            json_path=f"Regr_Age_vs_Epi_Age_{epi_clock}.json",
            # width = 837, # poster
            # height = 837 # poster
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
        get_eaa_res(data=data, epi_clock=epi_clock)
        #get_eaa_boxplot(data=data, epi_clock=epi_clock)


if __name__ == "__main__":
    main()
