#!/usr/local/bin/python

"""
A module generating figures for control probe fluorescence evaluation
"""

import sys

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plot_export_utils import export_decorated_fig_with_custom_name
from i18n import t

# Control probe type whose signal Illumina defines as the array background.
BACKGROUND_PROBE_TYPE = "NEGATIVE"

# Plot types carrying a background reference: those where the Illumina Controls
# Table expects every probe (TARGET_REMOVAL, RESTORATION, NEGATIVE) or a subset
# of the sub-probes (STAINING - DNP/Biotin Bgnd, SPECIFICITY_I - MM probes,
# BISULFITE_CONVERSION_I - U probes) to sit at background level. On EPIC/450K
# Subtype == Type for all of these, so the background-level sub-probes carry no
# distinct symbol and the reference is their only visual anchor. Types expected
# to be High or graded (EXTENSION, HYBRIDIZATION, BISULFITE_CONVERSION_II,
# SPECIFICITY_II, NON-POLYMORPHIC, NORM) are left out: comparing them with
# background carries no information. The rule follows the documented
# expectation, not the observed signal of any single run.
BACKGROUND_REFERENCE_TYPES = frozenset(
    {
        "TARGET_REMOVAL",
        "RESTORATION",
        "NEGATIVE",
        "STAINING",
        "SPECIFICITY_I",
        "BISULFITE_CONVERSION_I",
    }
)

# The 95% CI of the NEGATIVE mean is invisibly narrow at plot scale (+/-0.002
# log10 over ~28k points in a 69-sample EPIC run), so the band shows the spread
# of the background signal itself - the range points are actually compared with.
BACKGROUND_BAND_PERCENTILES = (5, 95)

# Below this many NEGATIVE measurements the 5th/95th percentile is an
# interpolation between the two extreme points; the mean line is drawn alone.
MIN_PROBES_FOR_BACKGROUND_BAND = 20

BACKGROUND_LINE_COLOR = "#3f3f3f"
BACKGROUND_BAND_COLOR = "#9e9e9e"
BACKGROUND_BAND_OPACITY = 0.25
BACKGROUND_ANNOTATION_FONT_SIZE = 12


def normalize_probe_type(probe_type: str) -> str:
    """Bring a control probe type to the naming used by BACKGROUND_REFERENCE_TYPES.

    ctrl_fluorescence_data.R derives Type from a curated column on 450K/EPIC and
    by splitting Probe_ID on EPICv2 (sesame's EPICv2.address carries no controls
    table); both paths yield the same upper-case, underscore-separated names, so
    this only guards the whitelist against a future change in that derivation.

    Args:
        probe_type (str): control probe type as stored in the parquet / passed in.

    Returns:
        str: upper-cased type with spaces replaced by underscores.
    """
    return str(probe_type).strip().upper().replace(" ", "_")


def get_background_reference(
    plot_data: pd.DataFrame,
) -> tuple[float, float | None, float | None] | None:
    """Summarise the background (NEGATIVE) signal of a run.

    Args:
        plot_data (pd.DataFrame): full control probe data (all types), i.e. the
            frame every plot invocation receives before filtering by type.

    Returns:
        tuple | None: (mean, band lower bound, band upper bound) of the NEGATIVE
        log_10_metric; the bounds are None when there are too few measurements
        for percentiles. None when no usable NEGATIVE measurement is present.
    """
    background = plot_data.loc[
        plot_data["Type"].map(normalize_probe_type) == BACKGROUND_PROBE_TYPE,
        "log_10_metric",
    ]
    # A control probe with a zero intensity gives log10(0) == -inf, which alone
    # would drag the mean to -inf (one such probe in a 69-sample EPIC run).
    background = background[np.isfinite(background)]

    if background.empty:
        print(
            f"Warning: no usable '{BACKGROUND_PROBE_TYPE}' measurements "
            "(absent, missing or non-finite). Plotting without a background "
            "reference.",
            file=sys.stderr,
        )
        return None

    mean = float(background.mean())

    if len(background) < MIN_PROBES_FOR_BACKGROUND_BAND:
        print(
            f"Warning: only {len(background)} '{BACKGROUND_PROBE_TYPE}' "
            "measurements. Plotting the background mean without a band.",
            file=sys.stderr,
        )
        return mean, None, None

    low, high = background.quantile(
        [percentile / 100 for percentile in BACKGROUND_BAND_PERCENTILES]
    )
    return mean, float(low), float(high)


def add_background_reference(
    fig: go.Figure, plot_data: pd.DataFrame, language: str = "en"
) -> None:
    """Draw the background level (NEGATIVE mean + percentile band) on a figure.

    Args:
        fig (go.Figure): figure to annotate, modified in place.
        plot_data (pd.DataFrame): full control probe data (all types).
        language (str): report language ("en"/"pl") for the reference label.
    """
    reference = get_background_reference(plot_data)

    if reference is None:
        return

    mean, low, high = reference

    if low is not None and high is not None:
        fig.add_hrect(
            y0=low,
            y1=high,
            fillcolor=BACKGROUND_BAND_COLOR,
            opacity=BACKGROUND_BAND_OPACITY,
            line_width=0,
            layer="below",
        )
        label = t(
            "plot.ctrl.background_band",
            language,
            low=BACKGROUND_BAND_PERCENTILES[0],
            high=BACKGROUND_BAND_PERCENTILES[1],
        )
    else:
        label = t("plot.ctrl.background_level", language)

    fig.add_hline(
        y=mean,
        line_dash="dash",
        line_color=BACKGROUND_LINE_COLOR,
        line_width=2,
        annotation_text=label,
        annotation_position="bottom right",
        annotation_font_size=BACKGROUND_ANNOTATION_FONT_SIZE,
    )


def get_ctrl_fluorescence_plot(
    plot_data: pd.DataFrame,
    ctrl_probe_type: str,
    column: str,
    hover_cols: list,
    language: str = "en",
) -> None:
    """A function generating control probe fluorescence plot, with coloring by Sample_Group if this column is provided

    Args:
        plot_data (pd.DataFrame): data used to generate a plot; all control probe
            types, as the NEGATIVE ones define the background reference
        ctrl_probe_type (str): a category of control probes (available categories depend on microarray type)
        column (str): a column, by which samples will be grouped at the plot
        hover_cols (list): a list of variables shown in a hover over sample point
        language (str): report language ("en"/"pl") for the intensity axis label
    """
    
    probe_data = plot_data[plot_data['Type'] == ctrl_probe_type]
    
    if probe_data.empty:
        print(f"Warning: no probes found for type '{ctrl_probe_type}'. Skipping plot.", file=sys.stderr)
        return

    if "Sample_Group" in probe_data.columns:
        fig = px.scatter(
            probe_data, x=column, y="log_10_metric", hover_data=hover_cols, color = "Sample_Group", symbol = "Subtype"
        )
    else:
        fig = px.scatter(
            probe_data, x=column, y="log_10_metric", hover_data=hover_cols, symbol = "Subtype"
        )

    unique_metric_types = probe_data['metric_type'].unique()
    if len(unique_metric_types) == 1 and unique_metric_types[0] == "total":
        metric_name = t("plot.ctrl.total_intensity", language)
    else:
        metric_name = t("plot.ctrl.max_intensity", language)

    # When a trace's subtype equals the probe type, the subtype name is redundant in the
    # legend. Plotly names such traces "{group}, {subtype}" — strip the subtype suffix.
    separator = ", "
    for trace in fig.data:
        if trace.name and trace.name.endswith(separator + ctrl_probe_type):
            trace.name = trace.name[: -len(separator + ctrl_probe_type)]

    fig.update_layout(
        yaxis={"title": f"log<sub>10</sub>{metric_name}<br>({ctrl_probe_type})"},
        scattermode="group",
    )

    if normalize_probe_type(ctrl_probe_type) in BACKGROUND_REFERENCE_TYPES:
        add_background_reference(fig=fig, plot_data=plot_data, language=language)

    export_decorated_fig_with_custom_name(
        fig=fig,
        json_path=f"{ctrl_probe_type}_by_{column}.json",
    )

def main():
    if len(sys.argv) != 6:
        print(
            "Usage: python ctrl_fluorescence_plots.py <path_to_ctrl_fluorescence_data: str> \
                <path_to_sample_sheet: str> <column: str> <ctrl_probe_type: str> \
                <report_language: en|pl>"
        )
        sys.exit(1)

    path_to_ctrl_fluorescence_data = sys.argv[1]
    path_to_sample_sheet = sys.argv[2]
    column = sys.argv[3]
    ctrl_probe_type = sys.argv[4]
    language = sys.argv[5]

    ctrl_fluorescence_data_raw = pd.read_parquet(path_to_ctrl_fluorescence_data)
    
    sample_sheet = pd.read_csv(path_to_sample_sheet)
    sample_sheet[["Sentrix_ID", "Sentrix_Position"]] = sample_sheet[
        "Array_Position"
    ].str.split("_", expand=True)

    ctrl_fluorescence_data = ctrl_fluorescence_data_raw.merge(sample_sheet, on="Sample_Name")

    get_ctrl_fluorescence_plot(
        plot_data=ctrl_fluorescence_data,
        ctrl_probe_type=ctrl_probe_type,
        column=column,
        hover_cols=sample_sheet.columns.to_list(),
        language=language,
    )

if __name__ == "__main__":
    main()