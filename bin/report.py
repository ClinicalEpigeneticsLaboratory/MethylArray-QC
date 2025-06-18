#!/usr/local/bin/python

"""
A module generating HTML report
"""

import sys
import datetime
import plotly.express as px
import json
from jinja2 import Template
import plotly.io as pio

def json_fig_to_html(json_path: str) -> str:
    """A function generating HTML div for a figure exported as JSON

    Args:
        json_path (str): path to a figure JSON file

    Returns:
        str: HTML code generated for a figure saved in JSON format
    """    
    try:
        fig = pio.read_json(f"{json_path}", skip_invalid = True)
        return fig.to_html(full_html=False, include_plotlyjs='cdn', config={"responsive": True})
    except Exception as e:
        print(f"❌ Failed to parse JSON Plotly figure from {json_path}: {e}")
        sys.exit(1)

def load_config_json(json_path: str) -> dict:
    """A function loading a JSON config (with exception handling)

    Args:
        json_path (str): path to a config exported as JSON file

    Returns:
        dict: a config with all exported workflow parameters, as dict
    """    
    try:
        with open(json_path) as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load config JSON from {json_path}: {e}")
        return {}

def get_nextflow_version(config: dict) -> str:
    """A function generating Nextflow version as formatted string

    Args:
        config (dict): a config with all exported workflow parameters, as dict

    Returns:
        str: Nextflow version, e.g. 24.10.5 (f"{major}.{minor}.{patch}")
    """    

    nf_ver = config.get("Nextflow_version", {})
    major = nf_ver.get("major", "NA")
    minor = nf_ver.get("minor", "NA")
    patch = nf_ver.get("patch", "NA")
    return f"{major}.{minor}.{patch}"

def get_run_times(config: dict) -> str:
    """A function generating a string containing information about:\n\
            1) workflow start date and time,\n\
            2) workflow completion date and time,\n\
            3) workflow duration
    Args:
        config (dict): a config with all exported workflow parameters, as dict

    Returns:
        str: a string containing:\n\
            1) workflow start date and time,\n\
            2) workflow completion date and time,\n\
            3) workflow duration
    """    
    start = get_formatted_time(config = config, type_value = "start")
    complete = get_formatted_time(config = config, type_value = "complete")
    duration = get_formatted_time(config = config, type_value = "duration")
    return f"{start} - {complete} (duration: {duration})"


def get_formatted_time(config: dict, type_value: str) -> str:
    """A function generating formatted string for workflow start/completion/duration time

    Args:
        config (dict): workflow parameters, from JSON 
        type_value (str): start, complete or duration

    Returns:
        str: formatted string with respective date and time
    """

    allowed_types = ["start", "complete", "duration"]
    if type_value not in allowed_types:
        raise ValueError(
            f"Incorrect value for 'type_VALUE' parameter provided — must be one of: {', '.join(allowed_types)}"
        )
    
    time_data = config.get(f"Workflow_{type_value}", {})

    if type_value == "duration":
        seconds = time_data.get("seconds", "NA")
        formatted_time = str(datetime.timedelta(seconds=seconds))
        return formatted_time
    else:
        day = int(time_data.get("dayOfMonth", "NA"))
        month = time_data.get("month", "NA").capitalize()
        year = int(time_data.get("year", "NA"))
        hour = int(time_data.get("hour", "NA"))
        minute = int(time_data.get("minute", "NA"))
        second = int(time_data.get("second", "NA"))
        return f"{day:02d} {month} {year} {hour:02d}:{minute:02d}:{second:02d}"

def flatten_dict(d, parent_key='', sep='.') -> dict:
    """A helper function flattening nested dict into dot-notated keys, e.g.:
    {'a': {'b': 1}} -> {'a.b': 1}

    Args:
        d (dict): a dictionary with nested parameters
        parent_key (str): a parent key for the currently processed key (default: '')
        sep (str): a separator for the new dictionary keys(default: .)

    Returns:
        dict: a flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def main():
    if len(sys.argv) != 7:
        print(
            "Usage: python report.py <html_template: str|Path> \
                <ao_plot_path: str|Path> <beta_distribution_plot: str|Path> \
                <nan_distribution_per_probe_plot: str|Path> \
                <nan_distribution_per_sample_plot: str|Path> \
                <config_json_path: str|Path>"
        )
        sys.exit(1)

    input_template_path = sys.argv[1]
    ao_plot_path = sys.argv[2]
    beta_distr_plot_path = sys.argv[3]
    heatmap_path = sys.argv[4]
    nan_distr_per_sample_path = sys.argv[5]
    config_json_path = sys.argv[6]

    output_report_path = "qc_report.html"

    config = load_config_json(config_json_path)
    nf_version = get_nextflow_version(config)

    flat_config = flatten_dict(config)

    substrings = [
        "Nextflow_version",
        "Workflow_start",
        "Workflow_duration",
        "Workflow_complete",
        "success",
        "err",
        "exitStatus",
        "cmdLine"
    ]

    flat_config_filtered = {
        k: v for k, v in flat_config.items()
        if not any(sub in k for sub in substrings)
    }   
    flat_config_ordered = {
        'Nextflow_version': nf_version,
        "Run_times": get_run_times(config),
        "Workflow_success": flat_config.get("Workflow_success", "NA"),
        "Workflow_errMsg": flat_config.get("Workflow_errMsg", "NA"),
        "Workflow_errDetails": flat_config.get("Workflow_errDetails", "NA"),
        "Workflow_exitStatus": flat_config.get("Workflow_exitStatus", "NA"),
        "Workflow_cmdLine": flat_config.get("Workflow_cmdLine", "NA"),
        **flat_config_filtered
    }

    report_jinja_data = {
        "beta_distr_plot": json_fig_to_html(beta_distr_plot_path),
        "nan_per_probe_plot": json_fig_to_html(heatmap_path),
        "nan_per_sample_plot": json_fig_to_html(nan_distr_per_sample_path),
        "workflow_params": flat_config_ordered
    }

    if ao_plot_path != "NO_FILE.txt":
        report_jinja_data["anomaly_det_plot"] = json_fig_to_html(ao_plot_path)
    else:
        report_jinja_data["anomaly_det_plot"] = None

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