#!/usr/local/bin/python

"""
A module generating HTML report
"""

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

def add_plot_section(report_sections: dict, id: str, title: str, paths: str|Path|list, description: str = None) -> dict:
    """A function generating a report section containing one plot

    Args:
        report_sections (dict): a dictionary containing report sections
        id (str): an id assigned to div with report section
        title (str): a title of report section
        paths (str | Path | list): one plot path or a list of plot paths
        description (str, optional): A description of plot section. Defaults to None.

    Returns:
        dict: a dictionary containing report sections with new report section added
    """    
    if isinstance(paths, str):
        paths = [paths]

    valid_paths = [(p, json_fig_to_html(p)) for p in paths if p and p not in ["no_ao_plot.txt", "no_ctrl_fluorescence_plots.txt", "no_epi_age.txt", "no_pca_kruskal.txt", "no_sex_inference.txt"]]

    if not valid_paths:
        return report_sections

    html_list = []
    for idx, (path, html) in enumerate(valid_paths):
        html_list.append({
            "plot_html": html,
            "plot_path": path,
            "plot_name": f"plot_{id}_{idx}"
        })

    report_section_dict = {
        "id": id,
        "title": title,
        "type": "plot-group",
        "html_list": html_list
    }

    if description is not None:
        report_section_dict["description"] = description

    report_sections.append(report_section_dict)

    return report_sections

def make_section(
    id: str,
    title: str,
    section_type: str,
    html: str = None,
    data: dict = None,
    html_list: List[str] = None,
    data_list: List[dict] = None,
    subsections: dict = None,
    description: str = None,
) -> dict:
    """A function creating a dictionary for single report section

    Args:
        id (str): an id assigned to div with report section
        title (str): a title of report section
        section_type (str): a type of section added - table, table-rows, plot, plot_group or plot+table
        html (str, optional): HTML for a single plot added to "plot" or "plot+table" report section. Defaults to None.
        data (dict, optional): a dictionary containing data used to generate a table in "table" or "plot+table" report section. Defaults to None.
        html_list (List[str], optional): A list of HTML strings for multiple plots added to a "plot-group" report section. Defaults to None.
        data_list (List[dict], optional): A list of dictionaries used to generate tables added to a "table-row-group" report section. Defaults to None.
        subsections (dict, optional): A dictionary containing data used to generate subsections within a report section. Defaults to None.
        description (str, optional): A description of report section. Defaults to None.
        
    Returns:
        dict: a dictionary defining single report section
    """    
    sect = {"id": id, "title": title, "type": section_type}
    if description is not None:
        sect["description"] = description
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
    elif section_type == "table-row-group":
        sect["data_list"] = data_list or []  # reuse the html_list arg for generality
    if subsections:
        sect["subsections"] = subsections
    return sect

def generate_subsection_list(
    main_id: str,
    subsection_list: List[str],
    title_prefix: str = None,
    plot_paths: List[str] = None,
    table_paths: List[str] = None

) -> List[Dict]:
    """A function generating a list of subsections for report section, with associated data.
    Data are dynamically mapped to a specific subsection, based on a current subsection_list element,
    typically contained within a path to specific table or plot.

    Args:
        main_id (str): a main div id for report section
        subsection_list (List[str]): a list of subsections to generate within report section (e.g. list of epigenetic clocks, list of column/workflow parameter values...)
        title_prefix (str, optional): A prefix added to subsection title. Defaults to None.
        plot_paths (List[str], optional): A list of paths to plots added to the whole report section. Defaults to None.
        table_paths (List[str], optional): A list of paths to tables added to the whole report section.. Defaults to None.

    Returns:
        List[Dict]: A list of dictionaries with defined structure and data for subsections of specific report section
    """    
    TITLE_MAP = {
        "area_plot": "PCA (general): Area plot",
        "PC_KW": "PCA: Kruskal-Wallis test results for each column",
        "scatter_matrix": "PCA: scatter matrix for each column",
        "probe": "Heatmap showing missing (NaN) values across samples and probes"
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

def add_section_with_subs(
    report_sections: List[Dict],
    id: str,
    title: str,
    paths: Union[str, Path, List[Union[str, Path]]],
    subsections: List[Dict] = None,
    description: str = None,
) -> List[Dict]:
    """A function adding a plot report section with subsections. If `subsections` is non-empty and valid, only add subsections under a parent shell.
    If no valid subsections, add a standalone plot or plot-group for `paths`.

    Args:
        report_sections (List[Dict]): a list of dictionaries containing report sections
        id (str): an id assigned to div with report section
        title (str): a title of report section
        paths (Union[str, Path, List[Union[str, Path]]]): _description_
        subsections (List[Dict], optional): A list of dictionaries with defined structure and plot HTML data for subsections of specific report section. Defaults to None.
        description (str, optional): A description of report section. Defaults to None.

    Returns:
        List[Dict]: a list of dictionaries containing report sections with new section divided to subsections added

    """    
    # Build subsections first
    subsecs_out = []
    if subsections:
        print("Received subsections:")
        for sub in subsections:
            print(sub["id"], sub.get("type"), "data_list" in sub)

            if sub.get("type") == "table-row-group":

                if "data_list" in sub and isinstance(sub["data_list"], list):
                    # ✅ Use provided data_list directly
                    subsecs_out.append(make_section(
                        id=sub["id"],
                        title=sub["title"],
                        section_type="table-row-group",
                        data_list=sub["data_list"],
                        description=description
                    ))
                    continue

                table_paths = sub.get("table_paths", [])
                if isinstance(table_paths, str):
                    table_paths = [table_paths]

                # Load all tables listed in table_paths
                tables_data = []
                for tpath in table_paths:
                    if tpath and tpath not in ["no_ao_plot.txt", "no_ctrl_fluorescence_plots.txt", "no_epi_age.txt", "no_pca_kruskal.txt", "no_sex_inference.txt"]:
                        table_data = load_table_data_json(tpath)
                        tables_data.append({
                            "title": Path(tpath).stem,
                            "data": table_data
                        })

                # Add a single subsection with all these tables
                subsecs_out.append(make_section(
                    id=sub["id"],
                    title=sub["title"],
                    section_type="table-row-group",
                    data_list=tables_data, 
                    description=description
                ))

                continue  # Skip rest of loop for this subsection

            plots = sub.get("plot_paths", [])
            tables = sub.get("table_paths", [])

            # Parse plots and tables
            plot_htmls = [
                (p, json_fig_to_html(p))
                for p in plots if p and p not in ["no_ao_plot.txt", "no_ctrl_fluorescence_plots.txt", "no_epi_age.txt", "no_pca_kruskal.txt", "no_sex_inference.txt"]
            ]

            table_data = [
                (t, load_table_data_json(t))
                for t in tables if t and t not in ["no_ao_plot.txt", "no_ctrl_fluorescence_plots.txt", "no_epi_age.txt", "no_pca_kruskal.txt", "no_sex_inference.txt"]
            ]

            # Determine section type
            has_table = bool(table_data)
            has_plots = bool(plot_htmls)

            if has_table and has_plots:
                # One table + one or many plots → plot+table
                section_data = {
                    "id": sub["id"],
                    "title": sub["title"],
                    "type": "plot+table",
                    "data": table_data[0][1],  # Use first table only
                }

                if len(plot_htmls) == 1:
                    section_data["html"] = plot_htmls[0][1]
                else:
                    section_data["html_list"] = [
                        {"plot_html": html, "plot_path": str(p), "plot_name": f"{sub['id']}_{i}"}
                        for i, (p, html) in enumerate(plot_htmls)
                    ]

                subsecs_out.append(make_section(**section_data, description=description))

            elif has_table:
                table_content = table_data[0][1]
                if isinstance(table_content, list):
                    section_type = "table-rows"
                else:
                    section_type = "table"

                subsecs_out.append(make_section(
                    id=sub["id"],
                    title=sub["title"],
                    section_type=section_type,
                    data=table_data[0][1],
                    description=description
                ))

            elif has_plots:
                if len(plot_htmls) == 1:
                    subsecs_out.append(make_section(
                        id=sub["id"],
                        title=sub["title"],
                        section_type="plot",
                        html=plot_htmls[0][1],
                        description=description
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
                        html_list=html_list,
                        description=description
                    ))

    # If subsections exist, add the parent section (shell) with subsections only
    if subsecs_out:
        report_sections.append(make_section(
            id=id,
            title=title,
            section_type="plot",  # no main plot here
            html="",  # empty or placeholder content
            subsections=subsecs_out,
            description=description
        ))
        return report_sections

    # No valid subsections: proceed with main paths
    paths_list = paths if isinstance(paths, (list, tuple)) else [paths]
    valid_main = [
        (p, json_fig_to_html(p))
        for p in paths_list
        if p and p not in ["no_ao_plot.txt", "no_ctrl_fluorescence_plots.txt", "no_epi_age.txt", "no_pca_kruskal.txt", "no_sex_inference.txt"]
    ]
    if not valid_main:
        return report_sections

    if len(valid_main) == 1:
        p, html = valid_main[0]
        report_sections.append(make_section(
            id=id,
            title=title,
            section_type="plot",
            html=html,
            description=description
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
            html_list=html_list,
            description=description
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

    config = load_table_data_json(config_json_path)
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
        "data": flat_config_ordered,
    })

    report_sections.append({
        "id": "qcSummary",
        "title": "Data QC - summary",
        "type": "table-rows",
        "data": qc_summary,
        "description": 'This section contains a table with QC statistics generated for provided IDAT files using SeSAME R package. For detailed explanations, refer to <a href="https://www.bioconductor.org/packages/devel/bioc/vignettes/sesame/inst/doc/QC.html">SeSAME documentation</a>.'
    })

    if unique_ctrl_probe_types != "no_probe_types":
        ctrl_fluorescence_plot_paths = ctrl_fluorescence_plot_paths.split(',')
        unique_ctrl_probe_types = sorted(unique_ctrl_probe_types.split(','))

        ctrl_fluorescence_subsections = generate_subsection_list(
            main_id="ctrlFluorescence",
            subsection_list=unique_ctrl_probe_types,
            plot_paths=ctrl_fluorescence_plot_paths,
            table_paths=None,
            title_prefix=None,
        )

        report_sections = add_section_with_subs(
            report_sections,
            id="ctrlFluorescence",
            title="Control probe fluorescence plots",
            paths="",          # ignored since subs exist
            subsections = ctrl_fluorescence_subsections,
            description="This section contains control probe fluorescence plots showing the intensity at different types of control probes present at Illumina microarrays. For details on how to interpret the results, see <a href='https://support.illumina.com/content/dam/illumina-support/documents/documentation/chemistry_documentation/infinium_assays/infinium_hd_methylation/beadarray-controls-reporter-user-guide-1000000004009-00.pdf'>Illumina BeadArray Reporter Software Guide</a>."
        )

    report_sections.append({
        "id": "preprocessingSummary",
        "title": "Data preprocessing - summary",
        "type": "table",
        "data": preprocess_summary,
        "description": "This section contains the summary of data preprocessing with SeSAME R package. For the details on the meaning of specific prep codes, please refer to <a href='https://www.bioconductor.org/packages/devel/bioc/vignettes/sesame/inst/doc/sesame.html'>SeSAME R package documentation</a>."
    })

    report_sections.append({
        "id": "imputationSummary",
        "title": "Data imputation - summary",
        "type": "table",
        "data": imputation_summary,
        "description": "This section contains imputation statistics after handling missing values based on user-specified thresholds and imputation methods"
    })

    if "no_ao_plot.txt" not in ao_plot_path:
        report_sections = add_plot_section(
            report_sections, 
            "anomalyDetection", 
            "Anomaly detection plot", 
            ao_plot_path,
            description="This section contains a plot visualising the identifiication of anomalies using Isolation Forest algorithm (for details see: <a href='https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html'>scikit-learn documentation</a>). Each sample is represented by one bar and a user-specified threshold is represented by red dashed line. Samples with bars exceeding threshold line should be considered as anomalies. "
        )
    
    if "no_sex_inference.txt" not in sex_inference_path:
        sex_inference_data = load_table_data_json(sex_inference_path)

        report_sections.append({
            "id": "sexInference",
            "title": "Sex inference",
            "type": "table-rows",
            "data": sex_inference_data,
            "description": "This section contains the results of sex inference using SeSAME method based on curated X-linked probes and Y chromosome probes (excluding pseudo-autosomal regions and XCI escapes - see <a href='https://www.bioconductor.org/packages/devel/bioc/vignettes/sesame/inst/doc/inferences.html'>SeSAME documentation</a> for details) and the comparison of results with sex declared in sample sheet. "
        })
    
    batch_subsections = generate_subsection_list(
        main_id="batchEffect",
        subsection_list=["Sentrix_ID", "Sentrix_Position"],
        table_paths=None,
        plot_paths=batch_effect_plot_paths,
        title_prefix="Mean beta per ",
    )

    report_sections = add_section_with_subs(
        report_sections,
        id="batchEffect",
        title="Batch effect evaluation",
        paths="",          # ignored since subs exist
        subsections = batch_subsections,
        description="This section contains batch effect evaluation plots showing mean methylation level per Sentrix_ID or Sentrix_Position across all CpG sites. Sentrix_IDs or Sentrix_Positions with mean methylation levels significantly deviating from the others are the potential source of batch effect and their exclusion from analysis should be considered."
    )

    report_sections = add_plot_section(report_sections, "betaDistribution", "Beta distribution plot", beta_distr_plot_path, description="This section contains a plot showing the kernel density (KDE) distribution of beta values for each sample across randomly selected n CpGs (CpG count selected by the user, default: 10k). Samples with a distribution significantly deviating from the others may be potential outliers.")

    missing_data_subsections = generate_subsection_list(
        main_id="missingData",
        subsection_list=["sample", "probe"],
        plot_paths=[nan_distr_per_sample_path, heatmap_path],
        table_paths=None,
        title_prefix="Missing data (NaN) distribution per ",
    )

    report_sections = add_section_with_subs(
        report_sections,
        id="missingData",
        title="Missing data evaluation",
        paths="",          # ignored since subs exist
        subsections = missing_data_subsections,
        description="This section contains plots allowing to identify samples and probes with high fraction of missing values:\
            <ul>\
                <li>a barplot representing the percentage of missing (NaN) probes per sample</li>\
                <li>a heatmap representing the distribution of missing (NaN) values across samples (in columns) and randomly selected n probes (in rows; n specified by the user)</li>\
            </ul>"
    )
    
    pca_plot_paths = pca_plot_paths.split(',')
    # pca_subsection_list = flat_config_ordered["pca_columns"].split(",")
    # pca_subsection_list.append("area_plot")
    # pca_subsection_list = ["area_plot", "PC_KW", "scatter_matrix"]

    pca_subsection_list = ["area_plot", "scatter_matrix"]

    pca_subsections = generate_subsection_list(
        main_id="pca",
        subsection_list=pca_subsection_list,
        plot_paths=pca_plot_paths,
        table_paths=None,
        title_prefix="PCA: "
    )

    pca_descr = ""

    #if "no_pca_kruskal.txt" not in pca_kruskal_paths:
    # if pca_kruskal_paths != "no_pca_kruskal.txt":
    pca_kruskal_paths = pca_kruskal_paths.split(',')

    table_group_data = []

    for path in pca_kruskal_paths:
        if "no_pca_kruskal.txt" not in path:
            table_data = load_table_data_json(path)
            colname = Path(path).stem.split("_")[-1]
            table_group_data.append({
                "title": f"Kruskal-Wallis for {colname}",
                "data": table_data
            })

    pca_kw_subsection = {
        "id": "pca_PC_KW",
        "title": "PCA: Kruskal-Wallis test results for each column",
        "type": "table-row-group",
        "data_list": table_group_data
    }

    # pca_kw_subsection = make_section(
    #     id="pca_PC_KW",
    #     title="PCA: Kruskal-Wallis test results for each column",
    #     section_type="table-row-group",
    #     data_list=table_group_data
    # )
    # pca_subsections.append(pca_kw_subsection)

    pca_subsections.append(pca_kw_subsection)
    # pca_kruskal_paths = pca_kruskal_paths.split(',')
    # pca_subsections = generate_subsection_list(
    #     main_id="pca",
    #     subsection_list=pca_subsection_list,
    #     #subsection_list=sorted(pca_subsection_list),
    #     plot_paths=pca_plot_paths,
    #     table_paths=pca_kruskal_paths,
    #     title_prefix="PCA: "
    #     #title_prefix="PCA: scatter matrix + Kruskal-Wallis - ",
    # )

    print("table_group_data:", table_group_data)

    if table_group_data:
        pca_descr = "This section contains the results of PCA analysis divided into the following subsections:<ul>\
            <li>an area cumulative variance plot for all principal components included in PCA analysis (number of components specified by the user)</li>\
            <li>results of Kruskal-Wallis test for each principal component (if there are at list 2 unique values in a selected column)</li>\
            <li>scatter matrix plot for first n components (n specified by the user)</li>\
            </ul>"
    else:
        pca_descr = "This section contains the results of PCA analysis divided into the following subsections:<ul>\
            <li>an area cumulative variance plot for all principal components included in PCA analysis (number of components specified by the user)</li>\
            <li>scatter matrix plot for first n components (n specified by the user)</li>\
            </ul>"
    # pca_descr = "This section contains the results of PCA analysis divided into the following subsections:<ul>\
    #     <li>an area cumulative variance plot for all principal components included in PCA analysis (number of components specified by the user)</li>\
    #     <li>one subsection for each column provided in workflow parameters - each containing:\
    #     <ul>\
    #         <li>results of Kruskal-Wallis test for each principal component</li>\
    #         <li>scatter matrix plot for first n components (n specified by the user)</li>\
    #     </ul>\
    #     </li></ul>"
# else:
#     pca_subsections = generate_subsection_list(
#         main_id="pca",
#         subsection_list=sorted(pca_subsection_list),
#         plot_paths=pca_plot_paths,
#         table_paths=None,
#         title_prefix="PCA: ",
#     )

    # pca_descr = "This section contains the results of PCA analysis divided into the following subsections:<ul>\
    #     <li>an area cumulative variance plot for all principal components included in PCA analysis (number of components specified by the user)</li>\
    #     <li>one subsection for each column provided in workflow parameters - each containing:\
    #     <ul>\
    #         <li>scatter matrix plot for first n components (n specified by the user)</li>\
    #     </ul>\
    #     </li></ul>"

    # pca_subsections = sorted(
    #     pca_subsections,
    #     key=lambda d: 0 if "area_plot" in d["id"] else 1
    # )

    # print(f"pca_subsections: {pca_subsections}")
    # print(f"Type of first element: {type(pca_subsections[0])}")
    # print(type(pca_subsections))  # should be list
    # print(type(pca_subsections[0]))  # should be dict
    # print(pca_subsections[0].keys())  # should be dict

    for sub in pca_subsections:
        print(f"SUBSECTION: {sub['id']}, type={sub.get('type')}, has data_list={bool(sub.get('data_list'))}")
    report_sections = add_section_with_subs(
        report_sections,
        id="pca",
        title="PCA",
        paths="",          # ignored since subs exist
        subsections = pca_subsections,
        description=pca_descr
    )
    
    if "no_epi_age.txt" not in epi_age_plot_paths:
        epi_age_plot_paths = epi_age_plot_paths.split(',')
        
        epi_age_subsections = generate_subsection_list(
            main_id="epiAge",
            subsection_list=flat_config_ordered["epi_clocks"].split(","),
            plot_paths=epi_age_plot_paths,
            table_paths=None,
            title_prefix="Epigenetic clock: ",
        )

        report_sections = add_section_with_subs(
            report_sections,
            id="epiAge",
            title="Epigenetic age plots",
            paths="",          # ignored since subs exist
            subsections = epi_age_subsections,
            description="This section contains the results of epigenetic age inference using \
                one or more of epigenetic clocks supported by <a href='https://github.com/yiluyucheng/dnaMethyAge'>dnaMethyAge R package</a> \
                (see the package website for full list of clocks and publications). Each subsection contains results for one clock. \
                For each clock, 2 types of plots are generated: <ul><li>a regression trendline of chronological and epigenetic age \
                <ul><li>general</li><li>if Sample_Group column present in sample sheet - trendlines for specific groups and general \
                trendline</li></ul><li>boxplots showing epigenetic age acceleration in each group (generated only if Sample_Group column present in sample sheet)</li></ul>"
        )

    for section in report_sections:
        if section["id"] == "pca":
            for sub in section.get("subsections", []):
                print(f"📦 SUB INSIDE PCA: {sub['id']} | type={sub.get('type')} | has data_list={bool(sub.get('data_list'))}")


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