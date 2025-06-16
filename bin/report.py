#!/usr/local/bin/python

"""
A module generating HTML report
"""

import sys
import plotly.express as px
from jinja2 import Template
import plotly.io as pio

def json_fig_to_html(json_path: str) -> str:
    try:
        fig = pio.read_json(f"{json_path}", skip_invalid = True)
        return fig.to_html()
    except Exception as e:
        print(f"❌ Failed to parse JSON Plotly figure from {json_path}: {e}")
        sys.exit(1)

def main():
    if len(sys.argv) != 6:
        print(
            "Usage: python report.py <html_template: str|Path> \
                <ao_plot_path: str|Path> <beta_distribution_plot: str|Path> \
                <nan_distribution_per_probe_plot: str|Path> \
                <nan_distribution_per_sample_plot: str|Path>"
        )
        sys.exit(1)

    input_template_path = sys.argv[1]
    ao_plot_path = sys.argv[2]
    beta_distr_plot_path = sys.argv[3]
    heatmap_path = sys.argv[4]
    nan_distr_per_sample_path = sys.argv[5]

    output_report_path = "qc_report.html"

    report_jinja_data = {
        "beta_distr_plot": json_fig_to_html(beta_distr_plot_path),
        "nan_per_probe_plot": json_fig_to_html(heatmap_path),
        "nan_per_sample_plot": json_fig_to_html(nan_distr_per_sample_path)
    }

    if ao_plot_path != "NO_FILE.txt":
        print(f"Reading plot: {ao_plot_path}")
        report_jinja_data["anomaly_det_plot"] = json_fig_to_html(ao_plot_path)

    with open(output_report_path, "w", encoding="utf-8") as output_file:
        with open(input_template_path) as template_file:
            j2_template = Template(template_file.read())

            try:
                rendered_html = j2_template.render(report_jinja_data)
            except Exception as e:
                print("❌ Template rendering failed:", e)
                sys.exit(2)
            output_file.write(rendered_html)

if __name__ == "__main__":
    main()