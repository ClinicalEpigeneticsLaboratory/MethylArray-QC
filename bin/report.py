#!/usr/local/bin/python

"""
A module generating HTML report
"""

from collections import defaultdict
import sys
import datetime
import json
from jinja2 import Template
import plotly.io as pio
from pathlib import Path
from typing import Union, List, Dict
import re

def json_fig_to_html(json_path: str) -> str:
    """A function generating HTML div for a figure exported as JSON

    Args:
        json_path (str): path to a figure JSON file

    Returns:
        str: HTML code generated for a figure saved in JSON format
    """    
    try:
        fig = pio.read_json(f"{json_path}", skip_invalid = True)
        return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
    except Exception as e:
        print(f"❌ Failed to parse JSON Plotly figure from {json_path}: {e}")
        sys.exit(1)

def load_table_data_json(json_path: str) -> dict:
    """A function loading a JSON data for the table (e.g. config; with exception handling)

    Args:
        json_path (str): path to data exported as JSON file

    Returns:
        dict: a dictionary with data read from JSON (e.g. config with all exported workflow parameters), as dict
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
    
    time_data = config.get(f"Workflow_{type_value}")

    if not time_data:
        return "Not available"

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

def flatten_dict(d: dict, parent_key: str='', sep: str='.') -> dict:
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

def add_plot_section(report_sections: dict, id: str, title: str, paths: str|Path|list) -> str:
    if isinstance(paths, str):
        paths = [paths]

    valid_paths = [(p, json_fig_to_html(p)) for p in paths if p and p != "NO_FILE.txt"]

    if not valid_paths:
        return report_sections

    html_list = []
    for idx, (path, html) in enumerate(valid_paths):
        html_list.append({
            "plot_html": html,
            "plot_path": path,
            "plot_name": f"plot_{id}_{idx}"
        })

    report_sections.append({
        "id": id,
        "title": title,
        "type": "plot-group",
        "html_list": html_list
    })

    return report_sections

# def add_column_group_table_section(report_sections: list, section_id: str, section_title: str, table_paths: list[str], group_label: str = "Sample") -> list:
#     """
#     Adds a 'column-group' section where each group gets a separate table.

#     Args:
#         report_sections (list): List of current sections.
#         section_id (str): Unique ID for the section.
#         section_title (str): Title shown in the report.
#         table_paths (list): List of JSON paths (each one should be a list of rows or a dict).
#         group_label (str): Label used for buttons (e.g. 'Sentrix_ID').

#     Returns:
#         list: Updated report_sections list.
#     """
#     group_data = {}

#     for path in table_paths:
#         if not path or path == "NO_FILE.txt":
#             continue

#         try:
#             data = load_table_data_json(path)
#             match = re.search(rf'{group_label}[-_]?([A-Za-z0-9]+)', path)
#             if match:
#                 group_key = match.group(1)
#             else:
#                 group_key = Path(path).stem

#             group_data[group_key] = {
#                 "type": "table-rows" if isinstance(data, list) else "table",
#                 "data": data
#             }
#         except Exception as e:
#             print(f"⚠️ Could not load table from {path}: {e}")
#             continue

#     if group_data:
#         report_sections.append({
#             "id": section_id,
#             "title": section_title,
#             "type": "column-group",
#             "group_label": group_label,
#             "items": group_data
#         })

#     return report_sections

# def add_column_group_table_and_plot_section(report_sections: list, section_id: str, section_title: str,
#                                             table_paths: list[str], plot_paths: list[str], group_label: str = "Sample") -> list:
#     """
#     Adds a 'column-group' section where each group shows both a table and a plot.

#     Args:
#         report_sections (list): List of sections to update.
#         section_id (str): Unique ID.
#         section_title (str): Title of section.
#         table_paths (list[str]): List of paths to table JSONs.
#         plot_paths (list[str]): List of paths to plot JSONs.
#         group_label (str): Label used for grouping (default: "Sample").

#     Returns:
#         list: Updated report_sections list.
#     """
#     group_data = {}

#     # Index tables by group ID
#     for path in table_paths:
#         if not path or path == "NO_FILE.txt":
#             continue
#         try:
#             data = load_table_data_json(path)
#             match = re.search(rf'{group_label}[-_]?([A-Za-z0-9]+)', path)
#             key = match.group(1) if match else Path(path).stem
#             group_data.setdefault(key, {})["table"] = {
#                 "type": "table-rows" if isinstance(data, list) else "table",
#                 "data": data
#             }
#         except Exception as e:
#             print(f"⚠️ Could not load table from {path}: {e}")

#     # Index plots by same group ID
#     for path in plot_paths:
#         if not path or path == "NO_FILE.txt":
#             continue
#         try:
#             html = json_fig_to_html(path)
#             match = re.search(rf'{group_label}[-_]?([A-Za-z0-9]+)', path)
#             key = match.group(1) if match else Path(path).stem
#             group_data.setdefault(key, {})["plot"] = {
#                 "type": "plot",
#                 "html": html
#             }
#         except Exception as e:
#             print(f"⚠️ Could not load plot from {path}: {e}")

#     # Final combined sections
#     final_items = {}
#     for key, contents in group_data.items():
#         if "plot" not in contents and "table" not in contents:
#             continue  # skip if empty

#         # Prioritize both; fallback to one
#         if "plot" in contents and "table" in contents:
#             final_items[key] = {
#                 "type": "composite",
#                 "plot": contents["plot"],
#                 "table": contents["table"]
#             }
#         elif "plot" in contents:
#             final_items[key] = contents["plot"]
#         elif "table" in contents:
#             final_items[key] = contents["table"]

#     if final_items:
#         report_sections.append({
#             "id": section_id,
#             "title": section_title,
#             "type": "column-group",
#             "group_label": group_label,
#             "items": final_items
#         })

#     return report_sections

def make_section(
    id: str,
    title: str,
    section_type: str,
    html: str = None,
    data=None,
    html_list=None,
    subsections=None
) -> dict:
    sect = {"id": id, "title": title, "type": section_type}
    if section_type == "table":
        sect["data"] = data or {}
    elif section_type == "table-rows":
        sect["data"] = data or []
    elif section_type == "plot":
        sect["html"] = html or ""
    elif section_type == "plot-group":
        sect["html_list"] = html_list or []
    elif section_type == "plot+table":
        sect["html"] = html or ""
        sect["data"] = data or {}
    if subsections:
        sect["subsections"] = subsections
    return sect

def generate_subsection_list(
    main_id: str,
    subsection_list: List[str],
    title_prefix: str,
    plot_paths: List[str],
    table_paths: List[str]

) -> List[Dict]:
    
    TITLE_MAP = {
        "area_plot": "PCA (general): Area plot"
    }
    
    subsections = []

    for subsection in subsection_list:

        title = ""

        title_base = TITLE_MAP.get(subsection)

        if title_base is None:
            if title_prefix is None:
                title = subsection
            else:
                title = f"{title_prefix} {subsection}"
        else:
            title = title_base

        regex = re.compile(fr"(?<![a-zA-Z]){re.escape(subsection)}(?=(_|$|[^a-zA-Z]))")

        matching_plots = [p for p in plot_paths if re.search(regex, p)] if plot_paths else []
        matching_tables = [t for t in table_paths if re.search(regex, t)] if table_paths else []

        subsections.append({
            "id": f"{main_id}_{subsection}",
            "title": title,
            "plot_paths": matching_plots,
            "table_paths": matching_tables
        })

    return subsections

def add_plot_section_with_subs(
    report_sections: List[Dict],
    id: str,
    title: str,
    paths: Union[str, Path, List[Union[str, Path]]],
    subsections: List[Dict] = None
) -> List[Dict]:
    """
    If `subsections` is non-empty and valid, only add subsections under a parent shell.
    If no valid subsections, add a standalone plot or plot-group for `paths`.
    """
    # Build subsections first
    subsecs_out = []
    if subsections:
        for sub in subsections:
            plots = sub.get("plot_paths", [])
            tables = sub.get("table_paths", [])

            # Parse plots and tables
            plot_htmls = [
                (p, json_fig_to_html(p))
                for p in plots if p and p != "NO_FILE.txt"
            ]

            table_data = [
                (t, load_table_data_json(t))
                for t in tables if t and t != "NO_FILE.txt"
            ]

            # Determine section type
            has_table = bool(table_data)
            has_plots = bool(plot_htmls)

            if has_table and has_plots:
                # One table + one or many plots → plot+table
                section_data = {
                    "id": sub["id"],
                    "title": sub["title"],
                    "section_type": "plot+table",
                    "data": table_data[0][1],  # Use first table only
                }

                if len(plot_htmls) == 1:
                    section_data["html"] = plot_htmls[0][1]
                else:
                    section_data["html_list"] = [
                        {"plot_html": html, "plot_path": str(p), "plot_name": f"{sub['id']}_{i}"}
                        for i, (p, html) in enumerate(plot_htmls)
                    ]

                subsecs_out.append(make_section(**section_data))

            elif has_table:
                subsecs_out.append(make_section(
                    id=sub["id"],
                    title=sub["title"],
                    section_type="table",
                    data=table_data[0][1]
                ))

            elif has_plots:
                if len(plot_htmls) == 1:
                    subsecs_out.append(make_section(
                        id=sub["id"],
                        title=sub["title"],
                        section_type="plot",
                        html=plot_htmls[0][1]
                    ))
                else:
                    html_list = [
                        {"plot_html": html, "plot_path": str(p), "plot_name": f"{sub['id']}_{i}"}
                        for i, (p, html) in enumerate(plot_htmls)
                    ]
                    subsecs_out.append(make_section(
                        id=sub["id"],
                        title=sub["title"],
                        section_type="plot-group",
                        html_list=html_list
                    ))

            # sub_paths = sub.get("paths") or sub.get("path")
            # sub_paths = sub_paths if isinstance(sub_paths, (list, tuple)) else [sub_paths]
            # valid = [
            #     (p, json_fig_to_html(p))
            #     for p in sub_paths
            #     if p and p != "NO_FILE.txt"
            # ]
            # if not valid:
            #     continue

            # if len(valid) == 1:
            #     p, html = valid[0]
            #     subsecs_out.append(make_section(
            #         id=sub["id"],
            #         title=sub["title"],
            #         section_type="plot",
            #         html=html
            #     ))
            # else:
            #     html_list = [
            #         {
            #             "plot_html": html,
            #             "plot_path": str(path),
            #             "plot_name": f"{sub['id']}_{idx}"
            #         }
            #         for idx, (path, html) in enumerate(valid)
            #     ]
            #     subsecs_out.append(make_section(
            #         id=sub["id"],
            #         title=sub["title"],
            #         section_type="plot-group",
            #         html_list=html_list
            #     ))

    # If subsections exist, add the parent section (shell) with subsections only
    if subsecs_out:
        report_sections.append(make_section(
            id=id,
            title=title,
            section_type="plot",  # no main plot here
            html="",  # empty or placeholder content
            subsections=subsecs_out
        ))
        return report_sections

    # No valid subsections: proceed with main paths
    paths_list = paths if isinstance(paths, (list, tuple)) else [paths]
    valid_main = [
        (p, json_fig_to_html(p))
        for p in paths_list
        if p and p != "NO_FILE.txt"
    ]
    if not valid_main:
        return report_sections

    if len(valid_main) == 1:
        p, html = valid_main[0]
        report_sections.append(make_section(
            id=id,
            title=title,
            section_type="plot",
            html=html
        ))
    else:
        html_list = [
            {
                "plot_html": html,
                "plot_path": str(path),
                "plot_name": f"{id}_{idx}"
            }
            for idx, (path, html) in enumerate(valid_main)
        ]
        report_sections.append(make_section(
            id=id,
            title=title,
            section_type="plot-group",
            html_list=html_list
        ))

    return report_sections



def main():
    if len(sys.argv) != 17:
        print(
            "Usage: python report.py <html_template: str|Path> \
                <qc_summary_path: str|Path> \
                <ctrl_fluorescence_plot_paths: str|Path> \
                <preprocess_summary_path: str|Path> \
                <imputation_summary_path: str|Path> \
                <ao_plot_path: str|Path> <beta_distribution_plot: str|Path> \
                <nan_distribution_per_probe_plot: str|Path> \
                <nan_distribution_per_sample_plot: str|Path> \
                <batch_effect_dir: str|Path> \
                <sex_inference_path: str|Path> \
                <config_json_path: str|Path> \
                <pca_kruskal_path: str|Path> \
                <pca_plot_paths: str|Path> \
                <epi_age_plot_paths: str|Path> \
                <unique_ctrl_probe_types: str>"
        )
        sys.exit(1)

    input_template_path = sys.argv[1]
    qc_summary_path = sys.argv[2]
    ctrl_fluorescence_plot_paths = sys.argv[3]
    preprocess_summary_path = sys.argv[4]
    imputation_summary_path = sys.argv[5]
    ao_plot_path = sys.argv[6]
    beta_distr_plot_path = sys.argv[7]
    heatmap_path = sys.argv[8]
    nan_distr_per_sample_path = sys.argv[9]
    batch_effect_plot_paths = sys.argv[10]
    sex_inference_path = sys.argv[11]
    config_json_path = sys.argv[12]
    pca_kruskal_paths = sys.argv[13]
    pca_plot_paths = sys.argv[14]
    epi_age_plot_paths = sys.argv[15]
    unique_ctrl_probe_types = sys.argv[16]


    output_report_path = "qc_report.html"

    batch_effect_plot_paths = batch_effect_plot_paths.split(',')
    ctrl_fluorescence_plot_paths = ctrl_fluorescence_plot_paths.split(',')
    pca_plot_paths = pca_plot_paths.split(',')
    pca_kruskal_paths = pca_kruskal_paths.split(',')
    epi_age_plot_paths = epi_age_plot_paths.split(',')
    unique_ctrl_probe_types = sorted(unique_ctrl_probe_types.split(','))

    config = load_table_data_json(config_json_path)
    sex_inference_data = load_table_data_json(sex_inference_path)
    qc_summary = load_table_data_json(qc_summary_path)
    preprocess_summary = load_table_data_json(preprocess_summary_path)
    imputation_summary = load_table_data_json(imputation_summary_path)
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

    report_sections = []

    # Add table section for workflow parameters
    report_sections.append({
        "id": "workflowParams",
        "title": "Workflow parameters",
        "type": "table",
        "data": flat_config_ordered
    })

    report_sections.append({
        "id": "qcSummary",
        "title": "Data QC - summary",
        "type": "table-rows",
        "data": qc_summary
    })

    # report_sections = add_plot_section(report_sections, "ctrlFluorescence", "Control probe fluorescence plots", ctrl_fluorescence_plot_paths)

    ctrl_fluorescence_subsections = generate_subsection_list(
        main_id="ctrlFluorescence",
        subsection_list=unique_ctrl_probe_types,
        plot_paths=ctrl_fluorescence_plot_paths,
        table_paths=None,
        title_prefix=None,
    )

    # TODO: generalize this to other cases (PCA, epi clocks, control fluorescence plots), generate data structure dynamically!!!
    report_sections = add_plot_section_with_subs(
        report_sections,
        id="ctrlFluorescence",
        title="Control probe fluorescence plots",
        paths="",          # ignored since subs exist
        subsections = ctrl_fluorescence_subsections,
    )

    report_sections.append({
        "id": "preprocessingSummary",
        "title": "Data preprocessing - summary",
        "type": "table",
        "data": preprocess_summary
    })

    report_sections.append({
        "id": "imputationSummary",
        "title": "Data imputation - summary",
        "type": "table",
        "data": imputation_summary
    })

    # Add plot sections
    if ao_plot_path != "NO_FILE.txt":
        report_sections = add_plot_section(report_sections, "anomalyDetection", "Anomaly detection plot", ao_plot_path)
    
    report_sections.append({
        "id": "sexInference",
        "title": "Sex inference",
        "type": "table-rows",
        "data": sex_inference_data
    })
    
    batch_subsections = generate_subsection_list(
        main_id="batchEffect",
        subsection_list=["Sentrix_ID", "Sentrix_Position"],
        table_paths=None,
        plot_paths=batch_effect_plot_paths,
        title_prefix="Mean beta per ",
    )

    report_sections = add_plot_section_with_subs(
        report_sections,
        id="batchEffect",
        title="Batch effect evaluation",
        paths="",          # ignored since subs exist
        subsections = batch_subsections,
    )

    report_sections = add_plot_section(report_sections, "betaDistribution", "Beta distribution plot", beta_distr_plot_path)

    missing_data_subsections = generate_subsection_list(
        main_id="missingData",
        subsection_list=["sample", "probe"],
        plot_paths=[nan_distr_per_sample_path, heatmap_path],
        table_paths=None,
        title_prefix="Missing data (NaN) distribution per ",
    )

    report_sections = add_plot_section_with_subs(
        report_sections,
        id="missingData",
        title="Missing data evaluation",
        paths="",          # ignored since subs exist
        subsections = missing_data_subsections,
    )

    # report_sections = add_plot_section(report_sections, "nanPerProbe", "Heatmap showing NaN per probe/sample", heatmap_path)
    # report_sections = add_plot_section(report_sections, "nanPerSample", "NaN per sample plot", nan_distr_per_sample_path)
    
    pca_subsection_list = flat_config_ordered["pca_columns"].split(",")
    pca_subsection_list.append("area_plot")

    pca_subsections = generate_subsection_list(
        main_id="pca",
        subsection_list=sorted(pca_subsection_list),
        plot_paths=pca_plot_paths,
        table_paths=pca_kruskal_paths,
        title_prefix="PCA: scatter matrix + Kruskal-Wallis - ",
    )

    pca_subsections = sorted(
        pca_subsections,
        key=lambda d: 0 if "area_plot" in d["id"] else 1
    )

    report_sections = add_plot_section_with_subs(
        report_sections,
        id="pca",
        title="PCA",
        paths="",          # ignored since subs exist
        subsections = pca_subsections,
    )

    # pca_kruskal_path = None

    # for pca_kruskal_path in pca_kruskal_paths:
    #     if pca_kruskal_path is None:
    #         raise ValueError("No pca_kruskal_path found!")
    #     else: 
    #         pca_kruskal_data = load_table_data_json(pca_kruskal_path)
    #         pattern = r"Sample_Group|Sentrix_ID|Sentrix_Position"
    #         match = re.search(pattern, pca_kruskal_path)
    #         column = match.group() 

    #         report_sections.append({
    #             "id": f"pcaKruskal{column}",
    #             "title": f"PCA (Kruskal-Wallis, {column})",
    #             "type": "table-rows",
    #             "data": pca_kruskal_data
    #         })

    # report_sections = add_plot_section(report_sections, "pcaPlots", "PCA (plots)", pca_plot_paths)
    
    epi_age_subsections = generate_subsection_list(
        main_id="epiAge",
        subsection_list=flat_config_ordered["epi_clocks"].split(","),
        plot_paths=epi_age_plot_paths,
        table_paths=None,
        title_prefix="Epigenetic clock: ",
    )

    report_sections = add_plot_section_with_subs(
        report_sections,
        id="epiAge",
        title="Epigenetic age plots",
        paths="",          # ignored since subs exist
        subsections = epi_age_subsections,
    )

    # Final template data
    report_jinja_data = {
        "report_sections": report_sections
    }

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
