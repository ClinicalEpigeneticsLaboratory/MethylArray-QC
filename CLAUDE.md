# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MethylArray-QC is a Nextflow DSL2 pipeline for processing and quality-assessing DNA methylation array data (IDAT files). It runs 13 sequential/parallel stages — QC, preprocessing, imputation, anomaly detection, sex inference, batch effect, beta/NaN distribution, PCA, epigenetic age inference, control probe visualization — and produces a final interactive HTML report.

## Commands

### Linting and Formatting (Python)
```bash
make black        # Format Python code with black
make isort        # Sort Python imports
make pylint       # Lint Python code
make dos2unix     # Normalize line endings in bin/
make i18n_check   # Validate the bin/i18n.py message catalog (key/placeholder/markup parity)
make dlint_python    # Lint Python Dockerfile with hadolint
make dlint_r_sesame  # Lint R SeSAME Dockerfile with hadolint
make dlint_r_clock   # Lint R clock Dockerfile with hadolint
make all          # Run all of the above
```

### Running the Pipeline
```bash
nextflow run main.nf \
  --idat_dir /path/to/idat/ \
  --sample_sheet sample_sheet.csv \
  --output_dir results/ \
  -profile docker
```

### Testing
Tests use [nf-test](https://www.nf-test.com/):
```bash
nf-test test tests/                    # Run all tests
nf-test test tests/main.nf.test        # Run a single test file
```

### Python Dependency Management
```bash
poetry install   # Install dependencies from pyproject.toml
poetry add <pkg> # Add a new package
```

## Architecture

### Pipeline Flow

```
IDAT files + sample_sheet.csv
  → ADDITIONAL_VALIDATORS_INIT
  → [parallel] QC (R/SeSAME) + PREPROCESS (R/SeSAME) + CTRL_FLUORESCENCE_DATA (R)
  → IMPUTE (Python/sklearn)
  → ADDITIONAL_VALIDATORS_AFTER_IMPUTE
  → [parallel analysis branches]
      ANOMALY_DETECTION | BETA_DISTRIBUTION | BATCH_EFFECT
      NAN_DISTRIBUTION_PER_SAMPLE | NAN_DISTRIBUTION_PER_PROBE
      PCA + KRUSKAL_WALLIS
      [optional] SEX_INFERENCE (R/SeSAME)
      [optional] EPIGENETIC_AGE_INFERENCE (R/dnaMethyAge) → EPIGENETIC_AGE_PLOTS (Python)
      [optional] CTRL_FLUORESCENCE_PLOTS (Python)
  → REPORT (Python/Jinja2 → qc_report.html)
```

### Key Directories

- **`main.nf`** — Entry point; validates params, wires all channels, handles conditional branches based on `params.infer_sex`, `params.infer_epi_age`, `params.ctrl_intens_plots`, and sample count thresholds (e.g. PCA/anomaly detection require >10 samples).
- **`modules/*.nf`** — One Nextflow process per module; each wraps a single script in `bin/`. Defines Docker container label, publishDir, inputs/outputs.
- **`subworkflows/`** — Higher-level groupings: `methylarrayqc_analysis.nf` (main analysis) and `report_generator.nf`.
- **`bin/*.py`** — Python analysis scripts (data processing, visualization, report assembly).
- **`bin/*.R`** — R scripts for SeSAME-based QC/preprocessing and epigenetic clock inference.
- **`lib/JsonWorkflowParamExporter.groovy`** — Groovy helper that serializes Nextflow workflow params + timestamps to JSON.
- **`templates/report.html`** — Bootstrap 5.3 + Plotly.js 3.0 Jinja2 template for the final interactive report.
- **`images/`** — Dockerfiles for three containers: `Python` (3.12-slim), `R_sesame` (R 4.4.1 + SeSAME), `R_clock` (R + dnaMethyAge).

### Data Format Conventions

- **Parquet** — All large tabular data between processes (e.g. `raw_mynorm.parquet`, `imputed_mynorm.parquet`, `ao_results.parquet`).
- **JSON** — Metadata, pipeline parameters, and serialized Plotly figure objects passed to the report.
- **HTML** — Final report output (`qc_report.html`).

### Container Labels

Each module declares one of three Docker container labels (mapped in `nextflow.config`):
- `python` — all Python scripts
- `r_sesame` — QC, preprocessing, sex inference, control probe data
- `r_clock` — epigenetic age inference

### Conditional Logic in main.nf

Several processes only run based on parameters or runtime conditions:
- `params.infer_sex` → `SEX_INFERENCE`
- `params.infer_epi_age` → `EPIGENETIC_AGE_INFERENCE` + `EPIGENETIC_AGE_PLOTS`
- `params.ctrl_intens_plots` → `CTRL_FLUORESCENCE_PLOTS`
- Sample count > 10 → enables `PCA`, `ANOMALY_DETECTION`

### Parameter Validation

All pipeline parameters are validated against `nextflow_schema.json` (JSON Schema Draft 2020-12) and the sample sheet against `sample_sheet_schema.json` at startup via `ADDITIONAL_VALIDATORS_INIT`.

### Report Generation

`bin/report.py` (1131 lines) aggregates all JSON plot files and parquet-derived summaries, renders them into `templates/report.html` via Jinja2. The REPORT Nextflow process has retry logic: memory scales as `4GB * attempt`, max 3 retries.
