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
8. **NaN distribution per sample plot**: shows the percentage of NaN probes per sample
9. **NaN distribution per probe plot**: shows a heatmap showing the distribution of NaN values across probes and samples
10. **PCA analysis**: generates:
   - scatter matrix for the first n components (specified by the user) with samples colored on visualisation using sample sheet columns selected by the user (Sentrix_ID, Sentrix_Position and/or Sample_Group)
   - an area plot visualising cumulative variance explained by all principal components in PCA (number of components specified by the user)
   - Kruskal-Wallis test results for each principal component and column specified by the user
11. **Epigenetic age inference (optional)**: Optional, allows to infer epigenetic age of samples using one or more of epigenetic clocks supported by `dnaMethyAge` R package (default: HannumG2013 & HorvathS2013, for full clock list see: https://github.com/yiluyucheng/dnaMethyAge) and for each clock generates:
   - a regression trendline of chronological and epigenetic age  
      - general
      - if Sample_Group column present in sample sheet - trendlines for specific groups and general trendline
   - boxplots showing epigenetic age acceleration in each group (generated only if Sample_Group column present in sample sheet)
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
echo $(java -version)

# Nextflow
curl -s https://get.nextflow.io | bash

# Add Nextflow executable to bin/
chmod +x nextflow
mv nextflow $HOME/bin/
```

### Input Data
- Directory containing IDAT files (`params.input`): Must include `.idat` or `.idat.gz` files corresponding to DNA methylation arrays.

### Configuration
The pipeline is preconfigured to use Docker containers for R and Python environments:
- R containers: 
   - `janbinkowski96/methyl-array-qc-r`
   - `methyl-array-qc-other`
- Python container: `janbinkowski96/methyl-array-qc-python`

## Usage

### 1. Parameters
The pipeline parameters can be adjusted as needed. Below are the key parameters and their descriptions:

- **General**:
  - `params.input`: Path to the directory containing IDAT files.
  - `params.output`: Path to the output directory.
  - `params.sample_sheet`: Path to sample sheet containing at least Sample_Name and Array_Position fields and in case additional analyses will be performed:
      - Sex (sex inference),
      - Age (epigenetic age inference),
      - Sample_Group (PCA - if needed for sample coloring, epigenetic age inference - epigenetic age acceleration comparison)
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

- **NaN distribution per probe**:
   - `params.nan_per_probe_n_cpgs`: Integer (default: 1000) specifying the number of CpGs randomly selected for NaN distribution per probe plot

- **PCA**:
   - `params.perc_pca_cpgs`: Integer, percentage of CpGs with highest variance selected for PCA analysis (1 to 100%)
   - `params.pca_columns`: Columns used in PCA analysis for sample coloring on a scatter matrix plot and for Kruskal-Wallis test (1-3 columns: Sentrix_ID, Sentrix_Position and/or Sample_Group, in any order, separated by commas without spaces)
   - `params.pca_number_of_components`: Number of all principal components for PCA analysis
   - `params.pca_matrix_PC_count`: Number of top principal components shown on PCA scatter matrix plot
- **Epigenetic age inference**:
   - `params.infer_epi_age`: Boolean (`true` or `false`, default: `true`) stating whether epigenetic age inference will be performed
   - `params.epi_clocks`: Epigenetic clocks used for epigenetic age inference (>= 1 clock, in any order, separated by commas without spaces; for full list of supported clocks use a function`dnaMethyAge::availableClock()` from `dnaMethyAge` R package)

In case you need additional information on parameters, run the following command:

```bash
nextflow run main.nf --help
```

### 2. Running the Pipeline
Run the pipeline using the following command:

```bash
nextflow run main.nf --input <path> --sample_sheet <path> --output <path>
```

or using `params.json` file containing at least `input`, `sample_sheet` and `output` fields.

```bash
nextflow run main.nf -params-file params.json
```

### Examplary `params.json` file:
```json
{
  "input": "/path/to/idats",
  "output": "/path/to/output",
  "sample_sheet": "/path/to/sample_sheet.csv",
  "prep_code": "QCDPB",
  "cpus": -1,
  "collapse_prefix": false,
  "collapse_prefix_method": "mean",
  "p_threshold": 0.2,
  "s_threshold": 0.2,
  "imputer_type": "knn",
  "contamination": "auto",
  "n_cpgs_beta_distr": 10000,
  "nan_per_probe_n_cpgs": 1000,
  "perc_pca_cpgs": 10,
  "pca_number_of_components": 5,
  "pca_columns": "Sentrix_ID,Sentrix_Position",
  "pca_matrix_PC_count": 5,
  "infer_sex": true,
  "infer_epi_age": true,
  "epi_clocks": "HannumG2013,HorvathS2013"
}
```

## Output
The pipeline produces the following outputs:

1. **Quality Control (`qc.parquet`)**:
   - Quality metrics for the samples.
2. **Raw Normalized Data (`raw_mynorm.parquet`)**:
   - Preprocessed methylation data.
3. **Imputed Data (`imputed_mynorm.parquet`, `impute_nan_per_probe.parquet`, `impute_nan_per_sample.parquet`)**:
   - Data with missing values imputed.
   - Imputation statistics: %NaN per sample, %NaN per probe.
4. **Anomaly Detection Results (`ao_results.parquet`)**:
   - Anomaly scores and classifications for each sample.
5. **Sex inference results (`inferred_sex.json`)**:
   - Declared sex, inferred sex and their comparison result for each sample.
6. **Batch effect evaluation results (`1.json, 2.json etc...`)**:
   - figures as JSON files (numbered from 1 to n...) in directories corresponding to columns (`Mean_beta_per_Sentrix_ID`, `Mean_beta_per_Sentrix_Position`) created automatically within output directory.
7. **Beta distribution plot (`beta_distribution.json`)**:
   - figure as JSON file.   
8. **NaN distribution per sample plot (`nan_distribution_per_sample.json`)**:
   - figure as JSON file
9. **NaN distribution per probe plot (`nan_distribution_per_probe.json`)**:
   - figure as JSON file
10. **PCA (`PCA_scatter_matrix_Sentrix_ID.json` + `PCA_PC_KW_test_Sentrix_ID.json`, `PCA_scatter_matrix_Sentrix_Position.json` + `PCA_PC_KW_test_Sentrix_Position.json` and/or `PCA_scatter_matrix_Sample_Group.json` + `PCA_PC_KW_test_Sample_Group.json`, `PCA_area.json`)**:
   - scatter matrix plots for first n components (n specified by the user), as JSON files (generated only figures for columns provided as a parameter)
   - results of Kruskal-Wallis test for each principal component, as JSON files (generated only for columns provided as parameter)
   - an area cumulative variance plot for all principal components included in PCA analysis (number of components specified by the user), as JSON file
11. **Epigenetic age inference** (`epi_clocks_res.parquet`, `Regr_Age_vs_Epi_Age_${epi_clock}.json`, `Epi_Age_Accel_${epi_clock}.json`):
   - results of epigenetic age inference and epigenetic age accelereation for all selected clocks, as parquet file,
   - linear regression trendline plot for each clock (`Regression` subdirectory), as JSON file,
   - (if `Sample_Group` column provided in sample sheet) epigenetic age acceleration grouped boxplots (group/color: `Sample_Group`) for each clock (`EAA` subdirectory), as JSON file.

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
- Output: `imputed_mynorm.parquet`, `impute_nan_per_probe.parquet`, `impute_nan_per_sample.parquet`.

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

### 8. NaN distribution per sample process
- Uses a Python script (`nan_distribution_per_sample.py`) to generate a barplot representing the percentage of NaN probes per sample.
- Output: `nan_distribution_per_sample.json`.

### 9. NaN distribution per probe process
- Uses a Python script (`nan_distribution_per_probe.py`) to generate a heatmap representing the distribution of NaN values across samples and randomly selected n probes.
- Output: `nan_distribution_per_probe.json`.

### 10. PCA process
- Uses a Python script (`pca.py`) to perform PCA on CpGs from imputed mynorm as features using number of components specified by the user and generating:
   - scatter matrix (matrices) visualising first n components (n: user-provided) with sample coloring based on column(s) provided by the user,
   - results of Kruskal-Wallis test for all components and column(s) specified by the user,
   - an area plot for all components in PCA specified by the user.
- Output: 
   - PCA scatter matrix plots for first n components: `PCA_scatter_matrix_Sentrix_ID.json`, `PCA_scatter_matrix_Sentrix_Position.json` and/or`PCA_scatter_matrix_Sample_Group.json`,
   - results of Kruskal-Wallis test for all components:
   `PCA_PC_KW_test_Sentrix_ID.json`, `PCA_PC_KW_test_Sentrix_Position.json` and/or`PCA_PCA_PC_KW_test_Sample_Group.json`,
   - PCA area plot for all components in the analysis: `PCA_area.json`.
### 11. Epigenetic age inference
- Uses an R script `epigenetic_age_inference.R` to infer epigenetic age using `dnaMethyAge` R package and a Python script `epigenetic_age_plots.py` to generate figures for each epigenetic clock:
   - linear regression trendline between chronological and epigenetic age (overall and per group, if this information provided)
   - (optional, if Sample_Group present in sample sheet) boxplots for epigenetic age acceleration
- Output:
   - results of epigenetic age inference and epigenetic age accelereation for all selected clocks: `epi_clocks_res.parquet`,
   - linear regression trendline plot for each clock (`Regression` subdirectory): `Regr_Age_vs_Epi_Age_${epi_clock}.json`,
   - (if `Sample_Group` column provided in sample sheet) epigenetic age acceleration grouped boxplots (group/color: `Sample_Group`) for each clock (`EAA` subdirectory): `Epi_Age_Accel_${epi_clock}.json`

## Known Issues and TODOs
- Implement tests for workflow and for specific processes
- Implement the output summary HTML report with embedded figures and tables
- anomaly detection:
1) implement more models
2) add parameter `contamination` to schema and `anomaly_detection.nf`
- fix path(s) issue, when input/output are relative
- add exemplary workflow (or other way to run a tool with exemplary data)
- define figures' common properties in `bin/decorators.py`
- organize process outputs in subdirectories (`publishDir`)
- add the visualisation of fluorescence on control probes (box per Slide, Array, Sample)
