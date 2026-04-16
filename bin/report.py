#!/usr/local/bin/python

"""
A module generating HTML report
"""

import os
import string
import sys
import time
import datetime
from dateutil import parser
import json
from jinja2 import Template, FileSystemLoader, Environment
import plotly.io as pio
from pathlib import Path
from typing import List, Dict, Union, Optional
import re
import htmlmin
import base64
import pprint

# helper function for debugging
def summarise_section(sec, indent=0):
    pad = "  " * indent
    print(f"{pad}- id: {sec.get('id')!r}, title: {sec.get('title')!r}, type: {sec.get('type')!r}")

    # Show which content‑keys are present (html / html_list / data / data_list)
    for key in ("html", "html_list", "data", "data_list"):
        if key in sec and sec[key]:
            if key in ("html", "html_list"):
                print(f"{pad}  • {key}: ✅ (non‑empty)")
            else:
                # for tables show length not whole content
                size = len(sec[key]) if isinstance(sec[key], (list, dict)) else "?"
                print(f"{pad}  • {key}: len={size}")

    # Recurse into subsections
    for sub in sec.get("subsections", []):
        summarise_section(sub, indent + 1)

def get_section_by_name(sections, name):
    """Return the first dict in the list with section_name == name."""
    return next((s for s in sections if s.get("id") == name), {})


def minify_html(rendered_html: str):
    # Minify output
    minified_html = htmlmin.minify(
        rendered_html,
        remove_comments=True,
        remove_empty_space=True,
        reduce_boolean_attributes=True,
        keep_pre=True,  # Preserve formatting in <pre> tags
    )

    return minified_html


def render_and_minify(
    report_sec_data: dict, in_template_path: str | Path, out_report_path: str | Path
):

    if not isinstance(in_template_path, Path):
        in_template_path = Path(in_template_path)
    if not isinstance(out_report_path, Path):
        out_report_path = Path(out_report_path)

    # Register the filter
    env = Environment(loader=FileSystemLoader(in_template_path.parent))
    env.filters["get_section"] = get_section_by_name

    j2_template = env.get_template(in_template_path.name)

    # Final template data
    report_jinja_data = {"report_sections": report_sec_data}

    try:
        rendered_html = j2_template.render(report_jinja_data)
        minified_html = minify_html(rendered_html)
    except Exception as e:
        print("❌ Template rendering failed:", e)
        sys.exit(2)

    with open(out_report_path, "w", encoding="utf-8") as output_file:
        output_file.write(minified_html)


def json_fig_to_html(json_path: str) -> str:
    """A function generating HTML div for a figure exported as JSON

    Args:
        json_path (str): path to a figure JSON file

    Returns:
        str: HTML code generated for a figure saved in JSON format
    """
    try:
        fig = pio.read_json(f"{json_path}", skip_invalid=True)
        # return fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
        return fig.to_html(
            full_html=False, include_plotlyjs="cdn", config={"responsive": True}
        )
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
    """A function returning the Nextflow version string from exported workflow config.

    Args:
        config (dict): a config with all exported workflow parameters, as dict

    Returns:
        str: Nextflow version, e.g. "24.10.5", or "NA" if absent
    """

    # nf_ver = config.get("nextflowVersion", {})
    # major = nf_ver.get("major", "NA")
    # minor = nf_ver.get("minor", "NA")
    # patch = nf_ver.get("patch", "NA")
    # return f"{major}.{minor}.{patch}"
    return config.get("nextflowVersion", {})


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
    # start = get_formatted_time(config=config, type_value="start")
    # complete = get_formatted_time(config=config, type_value="complete")
    # duration = get_formatted_time(config=config, type_value="duration")
    start = config["Workflow_start"]
    complete = config["Workflow_end"]
    duration = config["Workflow_duration"]
    return f"{start} - {complete} (duration: {duration})"


# def get_formatted_time(config: dict, type_value: str) -> str:
#     """A function generating formatted string for workflow start/completion/duration time

#     Args:
#         config (dict): workflow parameters, from JSON
#         type_value (str): start, complete or duration

#     Returns:
#         str: formatted string with respective date and time
#     """

#     allowed_types = ["start", "complete", "duration"]
#     if type_value not in allowed_types:
#         raise ValueError(
#             f"Incorrect value for 'type_VALUE' parameter provided — must be one of: {', '.join(allowed_types)}"
#         )
    
#     iso_string = config.get(f"Workflow_{type_value}")
#     if not iso_string:
#         return "Not available"

#     if type_value == "duration":
#         # fallback to old logic
#         seconds = config.get(f"Workflow_{type_value}", {}).get("seconds", 0)
#         return str(datetime.timedelta(seconds=seconds))

#     try:
#         dt = parser.isoparse(iso_string)
#         return dt.strftime("%d %B %Y %H:%M:%S")
#     except Exception:
#         return "Invalid timestamp"

    # time_data = config.get(f"Workflow_{type_value}")

    # if not time_data:
    #     return "Not available"

    # if type_value == "duration":
    #     seconds = time_data.get("seconds", "NA")
    #     formatted_time = str(datetime.timedelta(seconds=seconds))
    #     return formatted_time
    # else:
    #     day = int(time_data.get("dayOfMonth", "NA"))
    #     month = time_data.get("month", "NA").capitalize()
    #     year = int(time_data.get("year", "NA"))
    #     hour = int(time_data.get("hour", "NA"))
    #     minute = int(time_data.get("minute", "NA"))
    #     second = int(time_data.get("second", "NA"))
    #     return f"{day:02d} {month} {year} {hour:02d}:{minute:02d}:{second:02d}"


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
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


def add_plot_section(
    report_sections: dict,
    id: str,
    title: str,
    paths: str | Path | list,
    description: str = None,
) -> dict:
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

    valid_paths = [
        (p, json_fig_to_html(p))
        for p in paths
        if p
        and p
        not in [
            "no_ao_plot.txt",
            "no_ctrl_fluorescence_plots.txt",
            "no_epi_age.txt",
            "no_pca_kruskal.txt",
            "no_sex_inference.txt",
        ]
    ]

    if not valid_paths:
        return report_sections

    html_list = []
    for idx, (path, html) in enumerate(valid_paths):
        html_list.append(
            {"plot_html": html, "plot_path": path, "plot_name": f"plot_{id}_{idx}"}
        )

    report_section_dict = {
        "id": id,
        "title": title,
        "type": "plot-group",
        "html_list": html_list,
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
    data: dict | list | None = None,
    filename: str | None = None,       
    table_title: str | None = None,    
    html_list: list[str] | None = None,
    data_list: list[dict] | None = None,
    subsections: dict | list | None = None,
    description: str | None = None,
) -> dict:
    """Return a dictionary that describes a single report section."""
    sect = {"id": id, "title": title, "type": section_type}

    if description:
        sect["description"] = description

    # --------------------------
    if section_type == "table":
        sect["data"] = data or {}
    elif section_type == "table-rows":
        sect["data"] = data or []
    elif section_type == "plot":
        sect.update(html=html or "", plot_name=id)
    elif section_type == "plot-group":
        sect["html_list"] = html_list or []
    elif section_type == "plot+table":
        # allow ONE or MANY tables
        if data_list is not None:
            sect["data_list"] = data_list
        else:
            sect["data"] = data or {}
        # allow ONE or MANY plots
        if html_list:
            sect["html_list"] = html_list
        else:
            sect["html"] = html or ""
    elif section_type == "table-row-group":
        sect["data_list"] = data_list or []
    # --------------------------

    if filename:
        sect["filename"] = filename          
    if table_title:
        sect["table_title"] = table_title   

    if subsections:
        sect["subsections"] = subsections
    return sect

def generate_subsection_list(
    main_id: str,
    subsection_list: List[str],
    title_prefix: Optional[str] = None,
    plot_paths: Optional[List[str]] = None,
    *,
    tables: Optional[List[Dict]] = None,
    table_paths: Optional[List[str]] = None,
    table_titles: Optional[List[str]] = None,
    sub_descr_dict: Optional[Dict[str, str]] = None,
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
        table_titles (List[str], optional): A list of the titles of the tables added to the whole report section.. Defaults to None.

    Returns:
        List[Dict]: A list of dictionaries with defined structure and data for subsections of specific report section
    """

    TITLE_MAP = {
        "area_plot":      "PCA (general): Area plot",
        "PC_KW":          "PCA: Kruskal‑Wallis test results for each column",
        "scatter_matrix": "PCA: scatter matrix for each column",
        "probe":          "Heatmap showing missing (NaN) values",
    }

    # --- legacy shim: convert table_paths + table_titles -> tables ----
    if tables is None and table_paths:
        tables = []
        for i, tpath in enumerate(table_paths):
            tables.append(
                {
                    "path": tpath,
                    "table_title": table_titles[i] if table_titles else None,
                    "filename": Path(tpath).with_suffix(".csv").name,
                }
            )

    subsections: List[Dict] = []

    for subsection in subsection_list:

        # ---- build subsection title ----
        title = TITLE_MAP.get(subsection)
        if title is None:
            title = f"{title_prefix}{subsection}" if title_prefix else subsection

        regex = re.compile(rf"(?<![a-zA-Z]){re.escape(subsection)}(?=(_|$|[^a-zA-Z]))")

        # ---- match plots ----
        matching_plots = (
            [p for p in plot_paths if re.search(regex, p)] if plot_paths else []
        )

        # ---- match tables ----
        matching_tables: List[Dict] = []
        if tables:  # structured entries
            for tbl in tables:
                # choose regex target: path if present else use fallback ""
                tgt = tbl.get("path", "")
                if re.search(regex, tgt):
                    matching_tables.append(tbl)

        subsection_dict: Dict[str, Union[str, List]] = {
            "id":   f"{main_id}_{subsection}",
            "title": title,
            "plot_paths": matching_plots,
        }

        if matching_tables:
            subsection_dict["tables"] = matching_tables
        
        if sub_descr_dict is not None and subsection in sub_descr_dict:
            subsection_dict["description"] = sub_descr_dict[subsection]
            subsection_dict["show_description_in_subsections"] = True
        else:
            subsection_dict["show_description_in_subsections"] = False

        subsections.append(subsection_dict)

    return subsections

def load_table_data_ndjson(ndjson_path: str) -> list:
    """A function loading NDJSON data as a list of row dicts (for table-rows sections).
    NDJSON (Newline-Delimited JSON) has one JSON object per line, as produced by
    writeLines(rows_ndjson, path) in bin/epigenetic_age_inference.R.

    Args:
        ndjson_path (str): path to a NDJSON file

    Returns:
        list: list of dicts, one per row (matches the table-rows section format)
    """
    try:
        with open(ndjson_path) as f:
            return [json.loads(line) for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Failed to load NDJSON from {ndjson_path}: {e}")
        return []
    
def add_section_with_subs(
    report_sections: list[dict],
    id: str,
    title: str,
    paths: str | Path | list[str | Path],
    subsections: list[dict] | None = None,
    description: str | None = None,
) -> list[dict]:
    """Add a parent section; subsections may each carry ≥1 plot(s) and ≥1 table(s)."""

    INVALID = {
        "no_ao_plot.txt",
        "no_ctrl_fluorescence_plots.txt",
        "no_epi_age.txt",
        "no_pca_kruskal.txt",
        "no_sex_inference.txt",
    }
    is_ok = lambda p: p and p not in INVALID

    subs_out: list[dict] = []
    if subsections:
        for sub in subsections:
            sid, stitle = sub["id"], sub["title"]
            show_sub_descr = sub.get("show_description_in_subsections", False)
            sub_descr = sub.get("description") if show_sub_descr else None


            # ----- Handle tables -----
            table_entries = sub.get("tables")
            tables = []

            if table_entries:  # structured list with metadata
                for entry in table_entries:
                    if "data" in entry:
                        table = {
                            "data": entry["data"],
                            "filename": entry.get("filename"),
                            "table_title": entry.get("table_title")
                        }
                        tables.append(table)
                    elif "path" in entry and is_ok(entry["path"]):
                        data = load_table_data_json(entry["path"])
                        if data is not None:
                            table = {
                                "data": data,
                                "filename": entry.get("filename"),
                                "table_title": entry.get("table_title")
                            }
                            tables.append(table)
            else:  # fallback to old behavior using "table_paths"
                tab_paths = sub.get("table_paths", [])
                if isinstance(tab_paths, str):
                    tab_paths = [tab_paths]
                for p in tab_paths:
                    if is_ok(p):
                        data = load_table_data_json(p)
                        if data:
                            tables.append({"data": data})

            # special case: pre-assembled table-row-group
            if sub.get("type") == "table-row-group" and "data_list" in sub:
                data_list = sub["data_list"]
                if isinstance(data_list, list) and data_list:
                    subs_out.append(
                        make_section(
                            id=sid, title=stitle,
                            section_type="table-row-group",
                            data_list=data_list,
                            description=sub_descr
                        )
                    )
                continue

            # ----- Handle plots -----
            plt_paths = sub.get("plot_paths", [])
            if isinstance(plt_paths, str):
                plt_paths = [plt_paths]
            plot_htmls = [
                (p, json_fig_to_html(p)) for p in plt_paths if is_ok(p)
            ]

            has_tab = bool(tables)
            has_plot = bool(plot_htmls)

# ---------- PLOT + TABLE ----------
            if has_tab and has_plot:
                # ----- plots -----
                html_or_list = (
                    {"html": plot_htmls[0][1]}
                    if len(plot_htmls) == 1
                    else {"html_list": [
                        {"plot_html": h, "plot_name": f"{sid}_{i}"}
                        for i, (_, h) in enumerate(plot_htmls)
                    ]}
                )
                # ----- tables -----
                if len(tables) == 1:
                    t = tables[0]
                    tab_kwargs = {
                        "data": t["data"],
                        "filename": t.get("filename"),
                        "table_title": t.get("table_title"), 
                    }
                else:
                    tab_kwargs = {"data_list": [
                        {
                            "data": t["data"],
                            "filename": t.get("filename"),
                            "table_title": t.get("table_title"),
                        }
                        for t in tables
                    ]}

                subs_out.append(
                    make_section(
                        id=sid,
                        title=stitle,               # subsection headline
                        section_type="plot+table",
                        description=sub_descr,
                        **html_or_list,
                        **tab_kwargs
                    )
                )
        # ---------- TABLE‑only ----------
            elif has_tab:
                if len(tables) == 1:
                    t = tables[0]
                    sec_type = "table-rows" if isinstance(t["data"], list) else "table"
                    subs_out.append(
                        make_section(
                            id=sid,
                            title=stitle,
                            section_type=sec_type,
                            data=t["data"],
                            table_title=t.get("table_title"),     # <‑‑ renamed
                            filename=t.get("filename"),
                            description=sub_descr
                        )
                    )
                else:
                    subs_out.append(
                        make_section(
                            id=sid,
                            title=stitle,
                            section_type="table-row-group",
                            data_list=[
                                {
                                    "data": t["data"],
                                    "filename": t.get("filename"),
                                    "table_title": t.get("table_title"),
                                }
                                for t in tables
                            ],
                            description=sub_descr
                        )
                    )

            elif has_plot:
                if len(plot_htmls) == 1:
                    subs_out.append(
                        make_section(
                            id=sid, title=stitle, section_type="plot",
                            html=plot_htmls[0][1],
                            description=sub_descr
                        )
                    )
                else:
                    subs_out.append(
                        make_section(
                            id=sid, title=stitle, section_type="plot-group",
                            html_list=[
                                {"plot_html": h, "plot_name": f"{sid}_{i}"}
                                for i, (_, h) in enumerate(plot_htmls)
                            ],
                            description=sub_descr
                        )
                    )

    # ----- Parent shell -----
    if subs_out:
        report_sections.append(
            make_section(
                id=id, title=title, section_type="plot",
                html="", subsections=subs_out,
                description=description
            )
        )
        return report_sections

    # ----- Fall-back: section-level plot(s) -----
    paths_list = paths if isinstance(paths, (list, tuple)) else [paths]
    valid = [(p, json_fig_to_html(p)) for p in paths_list if is_ok(p)]
    if not valid:
        return report_sections

    if len(valid) == 1:
        report_sections.append(
            make_section(
                id=id, title=title, section_type="plot",
                html=valid[0][1],
                description=description
            )
        )
    else:
        report_sections.append(
            make_section(
                id=id, title=title, section_type="plot-group",
                html_list=[
                    {"plot_html": h, "plot_name": f"{id}_{i}"}
                    for i, (_, h) in enumerate(valid)
                ],
                description=description
            )
        )

    return report_sections

def main():
    if len(sys.argv) != 17:

        # sys.argv[0] is the script name itself
        print("Script name:", sys.argv[0])

        # sys.argv[1:] contains all arguments passed to the script
        print("Arguments:")
        for i, arg in enumerate(sys.argv[1:], start=1):
            print(f"Argument {i}: {arg}")

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
                <epi_age_paths: str|Path> \
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
    
    nan_distr_per_sample_paths = sys.argv[9]
    nan_distr_per_sample_paths = nan_distr_per_sample_paths.split(",")

    batch_effect_plot_paths = sys.argv[10]
    sex_inference_path = sys.argv[11]
    config_json_path = sys.argv[12]
    pca_kruskal_paths = sys.argv[13]
    pca_plot_paths = sys.argv[14]
    epi_age_paths = sys.argv[15]
    unique_ctrl_probe_types = sys.argv[16]

    print("Arguments:")
    for i, arg in enumerate(sys.argv[1:], start=1):
        print(f"Argument {i}: {arg}")

    output_report_path = "qc_report.html"

    batch_effect_plot_paths = batch_effect_plot_paths.split(",")

    config = load_table_data_json(config_json_path)
    qc_summary = load_table_data_json(qc_summary_path)
    preprocess_summary = load_table_data_json(preprocess_summary_path)
    imputation_summary = load_table_data_json(imputation_summary_path)
    nf_version = get_nextflow_version(config)

    flat_config = flatten_dict(config)

    substrings = [
        "nextflowVersion",
        "Workflow_start",
        "Workflow_duration",
        "Workflow_complete",
        "success",
        "err",
        "exitStatus",
        "cmdLine",
    ]

    flat_config_filtered = {
        k: v for k, v in flat_config.items() if not any(sub in k for sub in substrings)
    }
    flat_config_ordered = {
        "Nextflow_version": nf_version,
        "Run_times": get_run_times(config),
        "Workflow_success": flat_config.get("Workflow_success", "NA"),
        "Workflow_errMsg": flat_config.get("Workflow_errMsg", "NA"),
        "Workflow_errDetails": flat_config.get("Workflow_errDetails", "NA"),
        "Workflow_exitStatus": flat_config.get("Workflow_exitStatus", "NA"),
        "Workflow_cmdLine": flat_config.get("Workflow_cmdLine", "NA"),
        **flat_config_filtered,
    }

    # curr_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    curr_datetime = time.strftime("%Y-%m-%d_%H-%M-%S")

    report_sections = []

    report_sections.append(
        {
            "id": "qcSummary",
            "title": "Data QC - summary",
            "type": "table-rows",
            "data": qc_summary,
            "description": 'This section contains a table with QC statistics generated for provided IDAT files using SeSAME R package. For detailed explanations, refer to <a href="https://www.bioconductor.org/packages/devel/bioc/vignettes/sesame/inst/doc/QC.html">SeSAME documentation</a>.',
            "filename": "qc_summary",
        }
    )

    if unique_ctrl_probe_types != "no_probe_types":
        ctrl_fluorescence_plot_paths = ctrl_fluorescence_plot_paths.split(",")
        unique_ctrl_probe_types = sorted(unique_ctrl_probe_types.split(","))

        CTRL_DESC = {
            "STAINING": """
                <p><b>STAINING controls (sample-independent)</b> verify the fluorescent staining of
                probes after single‑base extension.<br><i>Expected</i>: a high signal in the
                Cy3/Cy5 channel depending on colour balance.</p>
            """,
            "EXTENSION": """
                <p><b>EXTENSION controls (sample-independent)</b> allow to check the performance of the single‑base extension
                step.<br><i>Expected</i>: a clear, high signal indicating the polymerase and dNTPs worked
                correctly.</p>
            """,
            "TARGET_REMOVAL": """
                <p><b>TARGET REMOVAL controls (sample-independent)</b> measure residual signal after the
                stripping step.<br><i>Expected</i>: very low intensity (near background).</p>
            """,
            "HYBRIDIZATION": """
                <p><b>HYBRIDIZATION controls (sample-independent)</b> use synthetic targets instead of amplified DNA to confirm the
                entire assay workflow.<br><i>Expected</i>: moderate to high signal.</p>
            """,
            "RESTORATION": """
                <p><b>RESTORATION controls (sample-independent, FFPE‑specific)</b> assess the effectiveness of
                the DNA restoration step in Infinium HD FFPE protocol.<br><i>Expected</i>: high signal suggesting successful repair of
                FFPE‑derived DNA.</p>
            """,
            "NORM": """
                <p><b>NORM controls (normalization control probe pairs, sample-independent)</b> 
                target non-CpG regions within housekeeping genes and are 
                used to measure dye performance and 
                color channel balance. For the Green channel, 
                CG controls values are used; for the Red 
                channel, AT controls values are used. 
                <br><i>Expected</i>: if there is no dye-bias, the intensity values 
                from the two probes of each pair would be 
                expected to be the same with a ratio close 
                to 1</p>
            """,
            "BISULFITE_CONVERSION_I": """
                <p><b>BISULFITE_CONVERSION_I controls (sample-dependent)</b> 
                assess the efficiency of bisulfite conversion of the input DNA
                using Infinium I probe design and allele-specific single 
                base extension
                <br><i>Expected</i>: High signal from converted 
                (C→T) probes and low signal from unconverted (C) 
                probes, indicating successful conversion. </p>
            """,
            "BISULFITE_CONVERSION_II": """
            <p><b>BISULFITE_CONVERSION_II controls (sample-dependent)</b> 
                assess the efficiency of bisulfite conversion of the input DNA
                using Infinium II probe design and allele-specific single 
                base extension
                <br><i>Expected</i>: High signal for probes that 
                target converted cytosines (C→T) and low signal 
                for unconverted Cs. Good conversion efficiency 
                results in high contrast.</p>
            """,
            "SPECIFICITY_I": """
            <p><b>SPECIFICITY_I controls (sample-dependent)</b> 
                are used to track the specificity of allele-specific extension for Infinium I probes
                <br><i>Expected</i>: High signal for matched probes; low or no signal for mismatched probes. Large signal separation is desired.</p>

            """,
            "SPECIFICITY_II": """
            <p><b>SPECIFICITY_II controls (sample-dependent)</b> 
                are used to track the specificity of allele-specific extension for Infinium II probes
                <br><i>Expected</i>: High signal for matched probes; low or no signal for mismatched probes. Large signal separation is desired.</p>
            """,
            "NON-POLYMORPHIC": """
            <p><b>NON-POLYMORPHIC controls (sample-dependent)</b> 
                are used to compare across samples the overall performance of the assay (from amplification to detection step)
                <br><i>Expected</i>: Consistently high signal across samples, indicating robust assay performance.</p>
            """,
            "NEGATIVE": """
            <p><b>NEGATIVE controls (sample-dependent)</b> 
                are randomly permutated sequences that should not hybridize to the genomic DNA.
                Their mean signal defines the background signal in the analysis.
                <br><i>Expected</i>: Low signal near background. Elevated signal may indicate 
                non-specific binding or contamination.</p>
            """
        }

        ctrl_fluorescence_subsections = generate_subsection_list(
            main_id="ctrlFluorescence",
            subsection_list=unique_ctrl_probe_types,
            plot_paths=ctrl_fluorescence_plot_paths,
            table_paths=None,
            title_prefix=None,
            sub_descr_dict=CTRL_DESC
        )

        report_sections = add_section_with_subs(
            report_sections,
            id="ctrlFluorescence",
            title="Control probe fluorescence plots",
            paths="",  # ignored since subs exist
            subsections=ctrl_fluorescence_subsections,
            description="""
            This section contains control probe 
                fluorescence plots showing the intensity at 
                    different types of control probes present 
                    at Illumina microarrays: 
                    <ul>
                    <li><b>Sample-independent controls:</b>: the controls not dependent on sample quality which are used to evaluate steps of the laboratory protocol (in terms of specific reagents and BeadChip itself), such as hybridization and staining</li>
                    <ul>
                    <li>STAINING</li>
                    <li>EXTENSION</li>
                    <li>TARGET_REMOVAL</li>
                    <li>HYBRIDIZATION</li>
                    <li>RESTORATION</li>
                    <li>NORM</li>
                    </ul>
                    <li><b>Sample-dependent controls:</b> probes used to assess sample DNA quality and the assay performance across samples</li>
                    <ul>
                    <li>BISULFITE_CONVERSION_I</li>
                    <li>BISULFITE_CONVERSION_II</li>
                    <li>SPECIFICITY_I</li>
                    <li>SPECIFICITY_II</li>
                    <li>NON-POLYMORPHIC</li>
                    <li>NEGATIVE</li>
                    </ul>
                    </ul>
                <br>If you need further details on how to interpret the results, please see: 
                    <ul>
                    <li><a href='https://support.illumina.com/content/dam/illumina-support/documents/documentation/chemistry_documentation/infinium_assays/infinium_hd_methylation/beadarray-controls-reporter-user-guide-1000000004009-00.pdf'>Illumina BeadArray Reporter Software Guide</a></li>
                    <li><a href='https://support.illumina.com/content/dam/illumina-support/courses/eval-inf-controls/story_content/external_files/Infinium_Controls_Training_Guide.pdf'>Infinium Controls Training Guide</a></li>
                    <li><a href='https://support-docs.illumina.com/ARR/Inf_HD_Methylation/Content/ARR/Methylation/SystemControlsIntro_fINF_mMeth.htm'>Infinium HD Methylation Assay System Controls official documentation</a></li>
                    <li><a href='https://support-docs.illumina.com/ARR/Inf_HD_Methylation/Content/ARR/Methylation/ControlBeadTypeIDs_fINF_mMeth.htm'>Infinium official Controls Table</a> (with useful tips on signal interpretation)</li>
                    <li>Xu, Z., Langie, S.A.S., De Boever, P. et al. RELIC: a novel dye-bias correction method for Illumina Methylation BeadChip. BMC Genomics 18, 4 (2017). https://doi.org/10.1186/s12864-016-3426-3</li>
                    </ul>
                """,
        )

    report_sections.append(
        {
            "id": "preprocessingSummary",
            "title": "Data preprocessing - summary",
            "type": "table",
            "data": preprocess_summary,
            "description": "This section contains the summary of data preprocessing with SeSAME R package. For the details on the meaning of specific prep codes, please refer to <a href='https://www.bioconductor.org/packages/devel/bioc/vignettes/sesame/inst/doc/sesame.html'>SeSAME R package documentation</a>.",
            "filename": "preprocessing_summary",
        }
    )

    report_sections.append(
        {
            "id": "imputationSummary",
            "title": "Data imputation - summary",
            "type": "table",
            "data": imputation_summary,
            "description": "This section contains imputation statistics after handling missing values based on user-specified thresholds and imputation methods",
            "filename": "imputation_summary",
        }
    )

    if "no_ao_plot.txt" not in ao_plot_path:
        report_sections = add_plot_section(
            report_sections,
            "anomalyDetection",
            "Anomaly detection plot",
            ao_plot_path,
            description="This section contains a plot visualising the identifiication of anomalies using Isolation Forest algorithm (for details see: <a href='https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html'>scikit-learn documentation</a>). Each sample is represented by one bar and a user-specified threshold is represented by red dashed line. Samples with bars exceeding threshold line should be considered as anomalies. ",
        )

    if "no_sex_inference.txt" not in sex_inference_path:
        sex_inference_data = load_table_data_json(sex_inference_path)

        report_sections.append(
            {
                "id": "sexInference",
                "title": "Sex inference",
                "type": "table-rows",
                "data": sex_inference_data,
                "description": "This section contains the results of sex inference using SeSAME method based on curated X-linked probes and Y chromosome probes (excluding pseudo-autosomal regions and XCI escapes - see <a href='https://www.bioconductor.org/packages/devel/bioc/vignettes/sesame/inst/doc/inferences.html'>SeSAME documentation</a> for details) and the comparison of results with sex declared in sample sheet. ",
                "filename": "sex_inference_results",
            }
        )

    batch_subsections = generate_subsection_list(
        main_id="batchEffect",
        subsection_list=["Sentrix_ID", "Sentrix_Position"],
        table_paths=None,
        plot_paths=batch_effect_plot_paths,
        title_prefix="Mean beta per ",
        sub_descr_dict=None
    )

    report_sections = add_section_with_subs(
        report_sections,
        id="batchEffect",
        title="Batch effect evaluation",
        paths="",  # ignored since subs exist
        subsections=batch_subsections,
        description="This section contains batch effect evaluation plots showing mean methylation level per Sentrix_ID or Sentrix_Position across all CpG sites. Sentrix_IDs or Sentrix_Positions with mean methylation levels significantly deviating from the others are the potential source of batch effect and their exclusion from analysis should be considered.",
    )

    report_sections = add_plot_section(
        report_sections,
        "betaDistribution",
        "Beta distribution plot",
        beta_distr_plot_path,
        description="This section contains a plot showing the kernel density (KDE) distribution of beta values for each sample across randomly selected n CpGs (CpG count selected by the user, default: 10k). Samples with a distribution significantly deviating from the others may be potential outliers.",
    )

    missing_data_plot_paths = nan_distr_per_sample_paths.append(heatmap_path)

    missing_data_subsections = generate_subsection_list(
        main_id="missingData",
        subsection_list=["sample", "probe"],
        plot_paths=missing_data_plot_paths,
        table_paths=None,
        title_prefix="Missing data (NaN) distribution per ",
        sub_descr_dict=None
    )

    report_sections = add_section_with_subs(
        report_sections,
        id="missingData",
        title="Missing data evaluation",
        paths="",  # ignored since subs exist
        subsections=missing_data_subsections,
        description="This section contains plots allowing to identify samples and probes with high fraction of missing values:\
            <ul>\
                <li>a barplots representing the percentage of missing (NaN) probes per sample</li>\
                <li>a heatmap representing the distribution of missing (NaN) values across samples (in columns) and randomly selected n probes (in rows; n specified by the user)</li>\
            </ul>",
    )

    pca_kruskal_paths = pca_kruskal_paths.split(",")
    pca_plot_paths = pca_plot_paths.split(",")

    all_pca_paths = pca_kruskal_paths + pca_plot_paths
    no_kruskal_present = any("no_pca_kruskal.txt" in p for p in all_pca_paths)
    no_plot_present = any("no_pca_plot.txt" in p for p in all_pca_paths)

    if not no_kruskal_present and not no_plot_present:
        if "no_pca_plot.txt" not in pca_plot_paths:
            pca_subsection_list = ["area_plot", "scatter_matrix"]

            pca_subsections = generate_subsection_list(
                main_id="pca",
                subsection_list=pca_subsection_list,
                plot_paths=pca_plot_paths,
                table_paths=None,
                title_prefix="PCA: ",
                sub_descr_dict=None
            )

            pca_descr = ""

        table_group_data = []

        for path in pca_kruskal_paths:
            if "no_pca_kruskal.txt" not in path:
                table_data = load_table_data_json(path)
                colname = table_data[0]["Column"]
                table_group_data.append(
                    {
                        "table_title": f"Kruskal-Wallis for {colname}",
                        "data": table_data,
                        "filename": f"PCA_kruskal_{colname}",
                    }
                )

        pca_kw_subsection = {
            "id": "pca_PC_KW",
            "title": "PCA: Kruskal-Wallis test results for each column",
            "type": "table-row-group",
            "data_list": table_group_data,
        }

        pca_subsections.append(pca_kw_subsection)

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

        report_sections = add_section_with_subs(
            report_sections,
            id="pca",
            title="PCA",
            paths="",  # ignored since subs exist
            subsections=pca_subsections,
            description=pca_descr,
        )

    if "no_epi_age.txt" not in epi_age_paths:
        epi_age_paths = epi_age_paths.split(",")
        epi_age_table_pattern = "_post_hoc_res"
        epi_age_summary_pattern = "epi_clocks_res.json"

        epi_age_summary_paths = [x for x in epi_age_paths if Path(x).name == epi_age_summary_pattern]
        epi_age_table_paths = [x for x in epi_age_paths if epi_age_table_pattern in x] or None

        if epi_age_table_paths is not None:
            epi_age_table_entries = [
                {
                    "path":  tpath,                               # file to load
                    "filename": Path(tpath).with_suffix(".csv").name,  # download name
                    "table_title":  "Post‑hoc test results (epigenetic age acceleration)"
                }
                for tpath in epi_age_table_paths
            ]
        else:
            epi_age_table_entries = None

        epi_age_plot_paths = [
            x for x in epi_age_paths
            if epi_age_table_pattern not in x and Path(x).name != epi_age_summary_pattern
        ]

        epi_age_subsections = []

        if epi_age_summary_paths:
            summary_data = load_table_data_ndjson(epi_age_summary_paths[0])
            if summary_data:
                epi_age_subsections.append({
                    "id": "epiAge_summary",
                    "title": "Summary: epigenetic age estimates and acceleration per sample",
                    "plot_paths": [],
                    "tables": [
                        {
                            "data": summary_data,
                            "filename": "epi_clocks_res",
                            "table_title": "Epigenetic age estimates and epigenetic age acceleration (all clocks)"
                        }
                    ],
                    "show_description_in_subsections": False,
                })

        epi_age_subsections += generate_subsection_list(
            main_id="epiAge",
            subsection_list=flat_config_ordered["epi_clocks"].split(","),
            plot_paths=epi_age_plot_paths,
            tables=epi_age_table_entries,
            title_prefix="Epigenetic clock: ",
            sub_descr_dict=None
        )

        report_sections = add_section_with_subs(
            report_sections,
            id="epiAge",
            title="Epigenetic age results",
            paths="",  # ignored since subs exist
            subsections=epi_age_subsections,
            description="This section contains the results of epigenetic age inference using \
                one or more of epigenetic clocks supported by <a href='https://github.com/yiluyucheng/dnaMethyAge'>dnaMethyAge R package</a> \
                (see the package website for full list of clocks and publications). Each subsection contains results for one clock. \
                For each clock, 2 types of plots are generated: <ul><li>a regression trendline of chronological and epigenetic age \
                <ul><li>general</li><li>if Sample_Group column present in sample sheet - trendlines for specific groups and general \
                trendline</li></ul><li>boxplots showing epigenetic age acceleration in each group (generated only if Sample_Group column present in sample sheet)</li></ul>",
        )

        report_sections.append(
            {
                "id": "workflowParams",
                "title": "Workflow parameters",
                "type": "table",
                "data": flat_config_ordered,
                "filename": f"methylarrayqc_workflow_params_{curr_datetime}",
            }
        )

        # Get the directory where the script resides
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Build absolute path to the logo file
        logo_path = os.path.join(script_dir, "..", "assets", "PUM__logo.png")

        logo_base64 = ""
        with open(logo_path, "rb") as f:
            logo_base64 = base64.b64encode(f.read()).decode()

        report_sections.append({"id": "footer", "footer_logo": logo_base64})

        render_and_minify(
            report_sec_data=report_sections,
            in_template_path=input_template_path,
            out_report_path=output_report_path,
        )


if __name__ == "__main__":
    main()
