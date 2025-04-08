#!/usr/local/bin/python

import pandas as pd
from pathlib import Path
import plotly.express as px
import sys

def getEpivsChronAgeRegrPlot(data: pd.DataFrame, epi_clock: str, hover_cols: list) -> None:
    
    if "Sample_Group" in data:
        fig = px.scatter(data, x="Age", y=f"mAge_{epi_clock}", color = "Sample_Group", trendline="ols", hover_data=hover_cols)
        overall_trendline = px.scatter(data, x = "Age", y=f"mAge_{epi_clock}", trendline="ols", trendline_scope="overall", trendline_color_override="black")
        fig.add_trace(overall_trendline.data[1])
    else:
        fig = px.scatter(data, x="Age", y=f"mAge_{epi_clock}", trendline="ols", hover_data=hover_cols)
    fig.update_layout(width=600, height=600, template="ggplot2")
    fig.write_json(file=f"Regression/Regr_Age_vs_Epi_Age_{epi_clock}.json", pretty=True)

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

    epi_clock_res = epi_age_res[["Sample", f"mAge_{epi_clock}", f"Age_Acceleration_{epi_clock}"]]
    epi_clock_res.rename(columns={"Sample": "Sample_Name"}, inplace=True)
    data = epi_clock_res.merge(sample_sheet, on = "Sample_Name")

    # Create the directory
    regr_out_dir_path = Path("Regression")
    regr_out_dir_path.mkdir(exist_ok=True)

    getEpivsChronAgeRegrPlot(data = data, epi_clock = epi_clock, hover_cols = sample_sheet.columns.to_list())

if __name__ == "__main__":
    main()