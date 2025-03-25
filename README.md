# Methylation Array QC 

## Overview
This Nextflow pipeline processes DNA methylation array data for precise quality assessment. 
The pipeline performs the following steps:

1. **Quality Control (QC)**: Generates quality metrics for the provided IDAT files.
2. **Preprocessing**: Normalizes data based on user-defined options (e.g., `prep_code`, collapsing settings).
3. **Imputation**: Handles missing data based on user-specified thresholds and imputation methods.
4. **Anomaly Detection**: Identifies anomalies using multiple machine learning algorithms (e.g., LOF, Isolation Forest, One-Class SVM).
5. **Sex inference (optional)**: Optional, infers sex using SeSAME method based on curated X-linked probes and Y chromosome probes (excluding pseudo-autosomal regions and XCI escapes) and compares it with sex declared in sample sheet.
6. **Batch effect evaluation plots**: show mean methylation level per Sentrix_ID or Sentrix_Position across all CpG sites
7. **Beta distribution plot**: shows the KDE distribution of beta values for each sample across randomly selected n CpGs (CpG count selected by the user, default: 10k)
8. **NaN distribution plot**: shows the percentage of NaN probes per sample
9. **PCA analysis**: generates 2D dotplot for the first 2 components with samples colored on visualisation using sample sheet columns selected by the user (Sentrix_ID, Sentrix_Position and/or Sample_Group) and a scree plot for number of components specified by the user

## Prerequisites

### Software Requirements
- Docker (enabled in the Nextflow config)
- Nextflow 23.10.0 or later
- NF test (installation: https://www.nf-test.com/installation/)
- Java 11 or later
- https://github.com/harrel56/json-schema

### Nextflow 
```
# Java
curl -s https://get.sdkman.io | bash
sdk install java 17.0.10-tem
echo java -version

# Nextflow
curl -s https://get.nextflow.io | bash

chmod +x nextflow
mkdir -p $HOME/.local/bin/

mv nextflow $HOME/.local/bin/
```

### Input Data
- Directory containing IDAT files (`params.input`): Must include `.idat` or `.idat.gz` files corresponding to DNA methylation arrays.

### Configuration
The pipeline is preconfigured to use Docker containers for R and Python environments:
- R container: `janbinkowski96/methyl-array-qc-r`
- Python container: `janbinkowski96/methyl-array-qc-python`

## Usage

### 1. Parameters
The pipeline parameters can be adjusted as needed. Below are the key parameters and their descriptions:

- **General**:
  - `params.input`: Path to the directory containing IDAT files.
  - `params.output`: Path to the output directory.
  - `params.sample_sheet`: Path to sample sheet containing at least Sample_Name and Array_Position fields (& Sex field in case sex inference will be performed).
  - `params.cpus`: Number of CPUs to use.

- **Preprocessing (Sesame)**:
  - `params.prep_code`: Preprocessing code for the `sesame` package (e.g., `QCDPB`, `SQCDPB`).
  - `params.collapse_prefix`: Boolean indicating whether to collapse probes with the same prefix.
  - `params.collapse_prefix_method`: Method for collapsing prefixes (e.g., `mean`, `minPval`).

- **Imputation**:
  - `params.p_threshold`: Fraction of NaN probes for which a CpG is considered corrupted and removed.
  - `params.s_threshold`: Fraction of NaN samples for which a sample is considered corrupted and removed.
  - `params.imputer_type`: Type of imputation (`mean`, `median`, `knn`).

- **Sex inference**:
   - `params.infer_sex`: Boolean (`true` or `false`) stating whether sex inference will be performed

- **Beta distribution**:
   - `params.n_cpgs_beta_distr`: Integer (default: 10000) specifying the number of CpGs randomly selected for beta distribution plot

- **PCA**:
   - `params.perc_pca_cpgs`: Integer, percentage of CpGs with highest variance selected for PCA analysis (1 to 100%)
   - `params.pca_columns`: Columns used in PCA analysis for sample coloring on a plot (1-3 columns: Sentrix_ID, Sentrix_Position and/or Sample_Group, in any order, separated by commas without spaces)

In case you need additional information on parameters, run the following command:

```bash
nextflow run main.nf --help
```

### 2. Running the Pipeline
Run the pipeline using the following command:

```bash
nextflow run main.nf -params-file params.config
```

### Example `params.config`:
```groovy
params {
    input = "/path/to/idats"
    output = "/path/to/output"
    cpus = 10

    // Sesame
    prep_code = "QCDPB"
    collapse_prefix = "TRUE"
    collapse_prefix_method = "mean"

    // Imputation
    p_threshold = 0.2
    s_threshold = 0.2
    imputer_type = "knn"

   //Sex inference
    infer_sex = true,

    //Beta distribution
    n_cpgs_beta_distr = 20000,

    //PCA
    perc_pca_cpgs = 20,
    pca_columns = "Sentrix_Position,Sample_Group,Sentrix_ID"
}
```

## Output
The pipeline produces the following outputs:

1. **Quality Control (`qc.parquet`)**:
   - Quality metrics for the samples.
2. **Raw Normalized Data (`raw_mynorm.parquet`)**:
   - Preprocessed methylation data.
3. **Imputed Data (`imputed_mynorm.parquet`)**:
   - Data with missing values imputed.
4. **Anomaly Detection Results (`ao_results.parquet`)**:
   - Anomaly scores and classifications for each sample.
5. **Sex inference results (`inferred_sex.json`)**:
   - Declared sex, inferred sex and their comparison result for each sample.
6. **Batch effect evaluation results (`1.json, 2.json etc...`)**:
   - figures as JSON files (numbered from 1 to n...) in directories corresponding to columns (`Mean_beta_per_Sentrix_ID`, `Mean_beta_per_Sentrix_Position`) created automatically within output directory.
7. **Beta distribution plot (`beta_distribution.json`)**:
   - figure as JSON file.   
8. **NaN distribution plot (`nan_distribution.json`)**:
   - figure as JSON file
9. **PCA (`PCA_2D_dot_Sentrix_ID.json` + `PCA_scree_Sentrix_ID.json`, `PCA_2D_dot_Sentrix_Position.json` + `PCA_scree_Sentrix_Position.json` and/or `PCA_2D_dot_Sample_Group.json` + `PCA_scree_Sample_Group.json`)**:
   - figures (2D dot plots for first 2 components and scree plots for all components) as JSON files (generated only figures for columns provided as a parameter)

## Process Details

### 1. QC Process
- Uses the `sesameQC_calcStats` function to calculate quality metrics for IDAT files.
- Output: `qc.parquet`.

### 2. Preprocessing Process
- Uses the `openSesame` function to preprocess IDAT files with user-specified options.
- Output: `raw_mynorm.parquet`.

### 3. Imputation Process
- Uses a Python script (`imputation.py`) to remove corrupted probes/samples and impute missing values.
- Supported imputers: `mean`, `median`, `knn`.
- Output: `imputed_mynorm.parquet`.

### 4. Anomaly Detection Process
- Uses a Python script (`anomaly_detection.py`) with algorithms such as LOF, Isolation Forest, and One-Class SVM to detect anomalies in the imputed data.
- Output: `ao_results.parquet`.

### 5. Sex inference process (optional)
- Uses a R script (`sex_inference.R`) to infer sex from imputed methylation beta values using SeSAME method based on curated X-linked probes and Y chromosome probes (excluding pseudo-autosomal regions and XCI escapes) and compares it with sex declared in sample sheet for each sample.
- Output: `inferred_sex.json`.

### 6. Batch effect evaluation process
- Uses a Python script (`batch_effect.py`) to generate figures with mean methylation per Slide (Senrix_ID) and per Array (Sentrix_Position).
- Output: directories `Mean_beta_per_Sentrix_ID` and `Mean_beta_per_Sentrix_Position` with figures (as JSON files) numbered from 1 to n, each presenting either 10 Sentrix_IDs or 10 Sentrix_Positions.

### 7. Beta distribution process
- Uses a Python script (`beta_distribution.py`) to generate a figure with KDE plot presenting the distribution of methylation beta values per sample.
- Output: `beta_distribution.json`.

### 8. NaN distribution process
- Uses a Python script (`nan_distribution.py`) to generate a barplot representing the percentage of NaN probes per sample.
- Output: `nan_distribution.json`.

### 9. PCA process
- Uses a Python script (`pca.py`) to perform PCA on CpGs from imputed mynorm as features using the first two components and generating 2D dotplot(s) visualising first 2 components with sample coloring based on column(s) provided by the user and a scree plots for all components specified by the user.
- Output: 
   - PCA 2D dotplots for first 2 components: `PCA_2D_dot_Sentrix_ID.json`, `PCA_2D_dot_Sentrix_Position.json` and/or`PCA_2D_dot_Sample_Group.json`,
   - PCA scree plot for all components specified by the user: `PCA_scree_Sentrix_ID.json`, `PCA_scree_Sentrix_Position.json` and/or`PCA_scree_Sample_Group.json`,

## Known Issues and TODOs
- Generate additional statistics (e.g. NaN distribution across probes).
- Implement multiprocessing for additional analyses.
- Implement tests for workflow and for specific processes
- Add epigenetic age inference
- Implement the output summary HTML report with embedded figures
- PCA: single scree plot as a separate process, single PCA as separate process (2D plots as separate process - ran 1 time per column)
