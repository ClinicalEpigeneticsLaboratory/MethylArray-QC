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

# Report output format selected via params.output_format and passed as the last
# CLI argument. One of:
#   "html" -> interactive qc_report.html (Plotly via CDN, accordion) - default
#   "pdf"  -> real, self-contained binary qc_report.pdf (each Plotly figure is
#             reconstructed in matplotlib; see bin/pdf_export_utils.py)
#   "json" -> single structured qc_report.json (raw Plotly specs + table data)
# Set once at the start of main(); read by the figure/section helpers below.
OUTPUT_FORMAT = "html"

# Placeholder files emitted by the workflow when an optional analysis is skipped.
# These must never be treated as real plot/table sources.
INVALID_SOURCE_PATHS = {
    "no_ao_plot.txt",
    "no_ctrl_fluorescence_plots.txt",
    "no_epi_age.txt",
    "no_pca_kruskal.txt",
    "no_sex_inference.txt",
}

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


# For html/json the run-time and workflow-status fields are finalised by
# workflow.onComplete via post-hoc string replacement of these placeholders. A
# binary PDF cannot be patched that way, so for the pdf format we instead compute
# the values directly at report-generation time (see compute_static_run_metadata):
# this is the last process in the pipeline and only runs when every upstream step
# has already succeeded, so the values are accurate (the run time excludes only
# the final publish step, ~1s; params.json keeps the byte-exact onComplete values).
ONCOMPLETE_SENTINELS = {
    "__PIPELINE_RUN_TIMES__",
    "__WORKFLOW_SUCCESS__",
    "__WORKFLOW_ERR_MSG__",
    "__WORKFLOW_ERR_DETAILS__",
    "__WORKFLOW_EXIT_STATUS__",
}


def compute_static_run_metadata(config: dict) -> dict:
    """Compute run-time/status fields for static (pdf) output at generation time.

    The workflow start is already in params.json (written before REPORT runs); the
    end is approximated by 'now', which - because REPORT is the final step - is
    within ~1s of the true workflow completion. The duration is computed from the
    UTC epoch start (Workflow_start_epoch) versus time.time(), so it is correct
    regardless of any host/container timezone difference. A report is only produced
    when every upstream step succeeded, so success/exitStatus are known too.
    """
    start_str = config.get("Workflow_start")
    start_epoch = config.get("Workflow_start_epoch")
    now_str = datetime.datetime.now().strftime("%d %B %Y %H:%M:%S")

    run_times = None
    if start_epoch is not None:
        try:
            total = max(int(time.time() - float(start_epoch)), 0)
            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            run_times = (f"{start_str or 'start'} - report generated "
                         f"(duration: {h:02d}:{m:02d}:{s:02d})")
        except Exception:
            run_times = None
    if run_times is None:
        run_times = (f"report generated {now_str}"
                     + (f"; started {start_str}" if start_str else ""))

    return {
        "Run_times": run_times,
        "Workflow_success": "true",
        "Workflow_exitStatus": "0",
        "Workflow_errMsg": "NA",
        "Workflow_errDetails": "NA",
    }


def finalize_static_workflow(workflow: dict, config: dict) -> dict:
    """Swap the onComplete placeholders for values computed at generation time."""
    meta = compute_static_run_metadata(config)
    return {k: (meta[k] if k in meta else v) for k, v in workflow.items()}


def render_pdf(
    report_sec_data: list,
    in_template_path: str | Path,
    out_report_path: str | Path,
):
    """Render a binary PDF that mirrors the interactive HTML report (pdf mode).

    The same assembled section list used for the HTML report is rendered through a
    print-only Jinja template (templates/report_pdf.html) and converted to PDF with
    WeasyPrint. Each Plotly figure has already been turned into a static <img> by
    json_fig_to_html (via Kaleido) when OUTPUT_FORMAT == "pdf", so the layout, fonts,
    tables and colours match report.html while the report stays fully inside the
    pipeline container. Requires weasyprint + kaleido in the python image (see
    pyproject.toml and images/Python/Dockerfile).
    """
    # Imported lazily so html/json runs do not pull in WeasyPrint.
    from weasyprint import HTML

    if not isinstance(in_template_path, Path):
        in_template_path = Path(in_template_path)

    env = Environment(loader=FileSystemLoader(in_template_path.parent))
    env.filters["get_section"] = get_section_by_name
    j2_template = env.get_template(in_template_path.name)

    try:
        rendered_html = j2_template.render({"report_sections": report_sec_data})
    except Exception as e:
        print("❌ PDF template rendering failed:", e)
        sys.exit(2)

    try:
        HTML(string=rendered_html, base_url=str(in_template_path.parent)).write_pdf(
            str(out_report_path)
        )
    except Exception as e:
        print("❌ WeasyPrint PDF generation failed:", e)
        sys.exit(2)


def section_to_json(sec: dict) -> dict:
    """Convert one assembled report section into a JSON-friendly dict (json mode).

    Rendered-HTML keys are dropped; Plotly figures are re-embedded as raw specs
    loaded from their source paths (figure -> single plot, figures -> list).
    Table content (data / data_list) is kept as-is. Recurses into subsections.
    """
    stype = sec.get("type")
    out: dict = {"id": sec.get("id"), "title": sec.get("title"), "type": stype}

    if sec.get("description"):
        out["description"] = sec["description"]
    if sec.get("filename"):
        out["filename"] = sec["filename"]
    if sec.get("table_title"):
        out["table_title"] = sec["table_title"]

    # ----- table data -----
    if sec.get("data") not in (None, "", [], {}):
        out["data"] = sec["data"]
    if sec.get("data_list"):
        out["data_list"] = sec["data_list"]

    # ----- single figure (plot / plot+table with one plot) -----
    if sec.get("plot_path"):
        fig = json_fig_to_dict(sec["plot_path"])
        if fig is not None:
            out["figure"] = fig

    # ----- multiple figures (plot-group / plot+table with several plots) -----
    if sec.get("html_list"):
        figs = []
        for entry in sec["html_list"]:
            path = entry.get("plot_path")
            if path:
                fig = json_fig_to_dict(path)
                if fig is not None:
                    figs.append(fig)
        if figs:
            out["figures"] = figs

    # ----- subsections -----
    if sec.get("subsections"):
        out["subsections"] = [section_to_json(s) for s in sec["subsections"]]

    return out


def render_json(
    report_sec_data: list, workflow: dict, out_report_path: str | Path
):
    """Render the structured JSON report (json mode).

    Produces a single qc_report.json with a top-level ``workflow`` dict (parameters
    and run metadata) and a ``sections`` list mirroring the report structure, with
    every plot embedded as a raw Plotly spec and every table as row data. The
    footer (logo) and the duplicate workflow-parameters section are omitted - the
    parameters live under the top-level ``workflow`` key instead.
    """
    exclude_ids = {"footer", "workflowParams"}
    json_sections = [
        section_to_json(sec)
        for sec in report_sec_data
        if sec.get("id") not in exclude_ids
    ]

    payload = {"workflow": workflow, "sections": json_sections}

    with open(out_report_path, "w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)


def json_fig_to_html(json_path: str) -> str:
    """Turn a figure JSON into the markup embedded for the current output format.

    - html: an interactive Plotly div (Plotly.js loaded once from the CDN).
    - pdf : a static <img> rasterised with Kaleido (WeasyPrint cannot run Plotly.js),
            so the same section structure carries an image instead of a live plot.
    - json: an empty string (the json export re-embeds the raw Plotly spec instead,
            via section_to_json / json_fig_to_dict).

    Args:
        json_path (str): path to a figure JSON file

    Returns:
        str: figure markup for html/pdf, or "" for the json format
    """
    if OUTPUT_FORMAT == "pdf":
        return json_fig_to_img(json_path)

    if OUTPUT_FORMAT != "html":
        return ""

    try:
        fig = pio.read_json(f"{json_path}", skip_invalid=True)
        return fig.to_html(
            full_html=False,
            include_plotlyjs="cdn",
            config={"responsive": True},
        )
    except Exception as e:
        print(f"⚠️  Failed to parse JSON Plotly figure from {json_path}: {e}")
        return '<span class="descr">[figure could not be rendered]</span>'


def json_fig_to_img(json_path: str) -> str:
    """Rasterise a Plotly figure JSON to a base64 <img> for the pdf format (Kaleido).

    WeasyPrint cannot execute Plotly.js, so for pdf output each figure is rendered to
    a static PNG with Kaleido and inlined as a data URI. The figure's own width/height
    (set by the export decorator) are honoured; scale=2 keeps it crisp in print. A
    single bad figure degrades to a short note rather than aborting the whole report.

    Args:
        json_path (str): path to a figure JSON file

    Returns:
        str: an <img> tag with the figure as a base64-encoded PNG data URI
    """
    try:
        fig = pio.read_json(f"{json_path}", skip_invalid=True)
        png = pio.to_image(fig, format="png", scale=2)
        b64 = base64.b64encode(png).decode()
        return f'<img src="data:image/png;base64,{b64}" alt="figure" />'
    except Exception as e:
        print(f"⚠️  Failed to render figure to image from {json_path}: {e}")
        return '<span class="descr">[figure could not be rendered]</span>'


def json_fig_to_dict(json_path: str) -> Optional[dict]:
    """Load a Plotly figure exported as JSON into a raw spec dict (for json mode).

    Figure files are written with ``fig.to_json()`` (see bin/decorators.py), so the
    file content is already a JSON-serialisable Plotly spec ({"data": [...],
    "layout": {...}}) and can be loaded directly.

    Args:
        json_path (str): path to a figure JSON file

    Returns:
        Optional[dict]: the Plotly figure spec, or None if it could not be loaded
    """
    try:
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON Plotly figure from {json_path}: {e}")
        return None


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
    """Returns a placeholder replaced with actual pipeline timing by workflow.onComplete.

    Timing is patched post-generation because workflow.start / workflow.complete
    (Nextflow's own timestamps) are only both available after the workflow ends,
    which is after this script has already run.

    Args:
        config (dict): a config with all exported workflow parameters, as dict

    Returns:
        str: placeholder string replaced by workflow.onComplete in main.nf
    """
    return "__PIPELINE_RUN_TIMES__"


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
    plot_path: str | None = None,
) -> dict:
    """Return a dictionary that describes a single report section.

    plot_path (when given) records the source figure JSON file for a single-plot
    section so that json mode can embed the raw Plotly spec. For multi-plot
    sections the source path is carried per entry inside html_list.
    """
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
        if plot_path:
            sect["plot_path"] = plot_path
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
            if plot_path:
                sect["plot_path"] = plot_path
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
                    {"html": plot_htmls[0][1], "plot_path": plot_htmls[0][0]}
                    if len(plot_htmls) == 1
                    else {"html_list": [
                        {"plot_html": h, "plot_name": f"{sid}_{i}", "plot_path": p}
                        for i, (p, h) in enumerate(plot_htmls)
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
                            plot_path=plot_htmls[0][0],
                            description=sub_descr
                        )
                    )
                else:
                    subs_out.append(
                        make_section(
                            id=sid, title=stitle, section_type="plot-group",
                            html_list=[
                                {"plot_html": h, "plot_name": f"{sid}_{i}", "plot_path": p}
                                for i, (p, h) in enumerate(plot_htmls)
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
                plot_path=valid[0][0],
                description=description
            )
        )
    else:
        report_sections.append(
            make_section(
                id=id, title=title, section_type="plot-group",
                html_list=[
                    {"plot_html": h, "plot_name": f"{id}_{i}", "plot_path": p}
                    for i, (p, h) in enumerate(valid)
                ],
                description=description
            )
        )

    return report_sections

def main():
    global OUTPUT_FORMAT

    if len(sys.argv) != 19:

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
                <unique_ctrl_probe_types: str> \
                <output_format: html|pdf|json> \
                <pdf_template: str|Path>"
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
    output_format = sys.argv[17].strip().lower()
    pdf_template_path = sys.argv[18]

    if output_format not in ("html", "pdf", "json"):
        print(
            f"❌ Invalid output_format '{output_format}'. Must be one of: html, pdf, json."
        )
        sys.exit(1)
    OUTPUT_FORMAT = output_format

    print("Arguments:")
    for i, arg in enumerate(sys.argv[1:], start=1):
        print(f"Argument {i}: {arg}")

    # Output filename depends on the selected format:
    #   html -> qc_report.html, pdf -> qc_report.pdf, json -> qc_report.json
    OUTPUT_FILENAMES = {
        "html": "qc_report.html",
        "pdf": "qc_report.pdf",
        "json": "qc_report.json",
    }
    output_report_path = OUTPUT_FILENAMES[OUTPUT_FORMAT]

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
        "Workflow_end",
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
        "Workflow_success": "__WORKFLOW_SUCCESS__",
        "Workflow_errMsg": "__WORKFLOW_ERR_MSG__",
        "Workflow_errDetails": "__WORKFLOW_ERR_DETAILS__",
        "Workflow_exitStatus": "__WORKFLOW_EXIT_STATUS__",
        "Workflow_cmdLine": flat_config.get("Workflow_cmdLine", "NA"),
        **flat_config_filtered,
    }

    # The html/json reports keep the onComplete sentinels (run time, success, exit
    # status, error) and are patched in place after the workflow ends. A binary PDF
    # cannot be patched that way, so for pdf we resolve those fields now - this is the
    # final step, so the values are accurate to within the closing publish (~1s).
    if OUTPUT_FORMAT == "pdf":
        flat_config_ordered = finalize_static_workflow(flat_config_ordered, config)

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

    # list.append returns None, so build the combined list explicitly - otherwise
    # the missing-data section would receive no plot paths at all.
    missing_data_plot_paths = nan_distr_per_sample_paths + [heatmap_path]

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

    # NOTE: the workflow-parameters table, footer and the final render must run for
    # every report regardless of whether epigenetic age was inferred - they are
    # therefore kept OUTSIDE the `if "no_epi_age.txt" ...` block above.
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

    # ----- Dispatch on the selected output format -----
    if OUTPUT_FORMAT == "json":
        render_json(
            report_sec_data=report_sections,
            workflow=flat_config_ordered,
            out_report_path=output_report_path,
        )
    elif OUTPUT_FORMAT == "pdf":
        # report_sections already carry the figures as static <img> (json_fig_to_html
        # in pdf mode) and the finalised workflow-params table; render them through the
        # print template with WeasyPrint.
        render_pdf(
            report_sec_data=report_sections,
            in_template_path=pdf_template_path,
            out_report_path=output_report_path,
        )
    else:  # html (default)
        render_and_minify(
            report_sec_data=report_sections,
            in_template_path=input_template_path,
            out_report_path=output_report_path,
        )


if __name__ == "__main__":
    main()
