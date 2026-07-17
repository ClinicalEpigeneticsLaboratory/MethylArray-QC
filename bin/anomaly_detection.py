#!/usr/local/bin/python

"""
An anomaly detection module
"""

import sys

import pandas as pd
import plotly.graph_objects as go
from decorators import update_and_export_plot
from i18n import t
from sklearn.ensemble import IsolationForest
# from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler


def ao(
    path_to_imputed_mynorm: str, contamination: str | float
) -> (pd.DataFrame, float):
    """A function performing anomaly detection on imputed mynorm

    Args:
        path_to_imputed_mynorm (str): path to imputed mynorm
        contamination (str | float): either auto or float (0, 0.5],\
            for more info see https://scikit-learn.org/stable/modules/outlier_detection.html

    Returns:
        (pd.DataFrame, float): A tuple containing anomaly detection results (pd.DataFrame) \
            and absolute threshold anomaly detection score
    """
    imputed_mynorm = pd.read_parquet(path_to_imputed_mynorm)

    if "CpG" in imputed_mynorm.columns:
        imputed_mynorm = imputed_mynorm.set_index("CpG")

    scaled_data = StandardScaler().fit_transform(imputed_mynorm.T)
    samples, cpgs = imputed_mynorm.columns, imputed_mynorm.index
    scaled_data = pd.DataFrame(scaled_data, index=samples, columns=cpgs)

    algorithms = {
        "IsolationForest": IsolationForest(
            random_state=101, contamination=contamination
        ),
    }

    anomaly_results = pd.DataFrame(index=samples)
    anomaly_results.index.name = "sample"

    for name, algorithm_instance in algorithms.items():
        algorithm_instance.fit(scaled_data)

        anomaly_results["|scores|"] = list(
            map(abs, algorithm_instance.score_samples(scaled_data))
        )
        anomaly_results["classes"] = list(
            map(
                lambda x: {"-1": "Anomaly", "1": "non-Anomaly"}.get(str(x)),
                algorithm_instance.predict(scaled_data),
            )
        )
        anomaly_results["threshold"] = [
            abs(algorithm_instance.offset_) for _ in range(len(samples))
        ]

        offset = abs(algorithm_instance.offset_)

    anomaly_results.to_parquet("ao_results.parquet")
    return anomaly_results, offset

@update_and_export_plot(
    "ao_plot.json",
    # One horizontal bar per sample makes this figure intrinsically tall. It is kept
    # as a single ordered trace (one bar per sample, coloured per class) so that the
    # interactive HTML report can scroll through every sample and, for the static PDF,
    # bin/report.py can slice the samples into fixed-size pages rendered at a constant
    # font (see paginate_anomaly_figure) - the label size then stays the same for any
    # cohort size instead of shrinking as samples are added. height_per_item keeps the
    # interactive figure tall enough that every sample stays labelled.
    width=1000,
    font_size=14,
    height_per_item=20,
)
def ao_plot(anomaly_results: pd.DataFrame, offset: float, language: str = "en") -> go.Figure:
    """A function generating the anomaly detection plot.

    Every sample is drawn as one horizontal bar in a single ordered trace, coloured
    red for anomalies and blue otherwise, with the score threshold as a red dashed
    line. Keeping all samples in one ordered trace (rather than one trace per class or
    a fixed column split) lets the PDF report re-paginate the samples across as many
    pages as needed at a constant font size (see bin/report.py paginate_anomaly_figure).

    Args:
        anomaly_results (pd.DataFrame): The results of anomaly\
            detection
        offset (float): the anomaly detection score\
            threshold differentiating anomaly from non-anomaly
        language (str): report language ("en"/"pl") for the axis/legend labels

    Returns:
        go.Figure: anomaly detection plot
    """
    # The class strings stay English (they are data values, also written to
    # ao_results.parquet); only the legend labels are localised, sharing catalog
    # keys with bin/report.py so the interactive and pdf anomaly legends never drift.
    colors = {"Anomaly": "red", "non-Anomaly": "blue"}
    legend_names = {
        "Anomaly": t("plot.anomaly.legend.anomaly", language),
        "non-Anomaly": t("plot.anomaly.legend.non_anomaly", language),
    }
    bar_colors = [colors.get(cls, "blue") for cls in anomaly_results["classes"]]

    fig = go.Figure()
    # Real data: a single ordered trace with a per-bar colour array. This preserves
    # the sample order and lets the PDF paginator slice samples across pages without
    # having to regroup traces.
    fig.add_trace(
        go.Bar(
            y=anomaly_results.index.tolist(),
            x=anomaly_results["|scores|"].tolist(),
            orientation="h",
            marker_color=bar_colors,
            showlegend=False,
        )
    )
    # A per-bar colour array draws no legend of its own, so add one empty proxy trace
    # per class purely to populate the legend.
    for cls, color in colors.items():
        fig.add_trace(
            go.Bar(
                y=[None],
                x=[None],
                orientation="h",
                marker_color=color,
                name=legend_names[cls],
                legendgroup=cls,
                showlegend=True,
            )
        )

    fig.add_vline(x=offset, line_width=1, line_dash="dash", line_color="red")
    fig.update_layout(
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02,
                "xanchor": "left", "x": 0}
    )
    fig.update_xaxes(title_text=t("plot.anomaly.xaxis", language))
    fig.update_yaxes(title_text=t("plot.anomaly.yaxis", language))
    return fig


def main():
    if len(sys.argv) != 4:
        print(
            """Usage: python anomaly_detection.py <path_to_imputed_mynorm: str>\
                <contamination: str | float> <report_language: en|pl>"""
        )
        sys.exit(1)

    path_to_imputed_mynorm, contamination, language = sys.argv[1:]

    try:
        contamination = float(contamination)
    except ValueError:
        pass

    results, offset = ao(path_to_imputed_mynorm, contamination)
    ao_plot(results, offset, language)


if __name__ == "__main__":
    main()
