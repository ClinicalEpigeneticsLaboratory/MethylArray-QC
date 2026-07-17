# Exemplary Workflow

This directory contains everything needed to run MethylArray-QC on a small
public dataset and see the full pipeline in action.

## Dataset

15 EPIC array samples from GEO series
[GSE86831](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE86831)
(Pidsley et al. 2016, *Genome Biology* — critical evaluation of the EPIC BeadChip).
The dataset contains five cell/tissue types across four Sentrix chips:

| Sample_Group | Samples | Description |
|---|---|---|
| LNCaP | 2 | Prostate cancer cell line |
| PrEC | 2 | Primary prostate epithelial cells |
| CAF | 3 | Cancer-associated fibroblasts |
| NAF | 3 | Non-malignant tissue fibroblasts |
| GuthrieCard | 5 | Archival infant blood cards |

With 15 samples and 4 Sentrix IDs, all pipeline stages are exercised:
QC, preprocessing, imputation, anomaly detection, PCA, batch effect evaluation,
beta distribution, NaN distribution, control probe intensity plots, sex inference,
and epigenetic age inference (HannumG2013 and HorvathS2013 clocks).

> **Note:** The `Sex` and `Age` values in `sample_sheet.csv` are synthetic
> placeholder values added for demonstration purposes — they are not from the
> original study. The GEO record for GSE86831 does not include donor age or sex
> metadata. Results from sex inference and epigenetic age inference on this
> dataset should be treated as illustrative only.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed and running
- [Nextflow](https://www.nextflow.io/docs/latest/install.html) >= 23.10.0
- ~1.5 GB free disk space (373 MB tar + ~400 MB extracted IDATs + pipeline results)
- Internet connection for the initial data download

## Step 1: Download Example Data

From the repository root:

```bash
bash examples/fetch_example_data.sh
```

This downloads `GSE86831_RAW.tar` (~373 MB) from the NCBI GEO FTP server into
`examples/idats/`, extracts the 15 sample pairs, and renames files to the
format expected by the pipeline. The script is idempotent — running it again
skips both the download and extraction if the files are already in place.

## Step 2: Run the Pipeline

> **Important:** All commands below must be run from the **repository root** directory
> (the directory containing `main.nf`). The params file uses paths relative to that root.

```bash
# Option A: using the params file directly
nextflow run main.nf -params-file examples/params.json

# Option B: using the test profile (nf-core convention)
nextflow run main.nf -profile test

# Option C: using Make
make run_example
```

Docker images are pulled automatically on first run (~1-2 GB, one-time cost).

## Step 3: View the Report

Open `examples/results/qc_report.html` in a browser.
All pipeline outputs (Parquet files, JSON figures) are also in `examples/results/`.

## Approximate Runtime

| Hardware | First run | Subsequent runs |
|---|---|---|
| Laptop (4 CPUs, Docker) | ~30-50 min | ~20-30 min |
| Workstation (8+ CPUs) | ~15-25 min | ~10-15 min |

First-run time includes Docker image pulls. Nextflow caches intermediate results
in the `work/` directory, so re-runs with changed parameters are faster.

## Cleanup

```bash
make clean_example    # removes examples/idats/ and examples/results/
```

## Using Your Own Data

To use this example as a template for your own dataset:

1. Replace `examples/idats/` with a directory containing your IDAT files.
2. Update `examples/sample_sheet.csv` with your sample metadata (real `Sex` and
   `Age` values if available).
3. Adjust `examples/params.json` as needed (e.g. change `prep_code` for your
   array type, tune thresholds).

## Citation

Pidsley R et al. (2016) Critical evaluation of the Illumina MethylationEPIC
BeadChip microarray for whole-genome DNA methylation profiling.
*Genome Biology* 17:208. https://doi.org/10.1186/s13059-016-1066-1

GEO accession: GSE86831 (https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE86831)
