# Methylation Array QC 

## Overview
This Nextflow pipeline processes DNA methylation array data for precise quality assessment. 
The pipeline performs the following steps:

1. **Quality Control (QC)**: Generates quality metrics for the provided IDAT files.
2. **Preprocessing**: Normalizes data based on user-defined options (e.g., `prep_code`, collapsing settings).
3. **Imputation**: Handles missing data based on user-specified thresholds and imputation methods.
4. **Anomaly Detection**: Identifies anomalies using multiple machine learning algorithms (e.g., LOF, Isolation Forest, One-Class SVM).

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
  - `params.cpus`: Number of CPUs to use.

- **Preprocessing (Sesame)**:
  - `params.prep_code`: Preprocessing code for the `sesame` package (e.g., `QCDPB`, `SQCDPB`).
  - `params.collapse_prefix`: Boolean indicating whether to collapse probes with the same prefix.
  - `params.collapse_prefix_method`: Method for collapsing prefixes (e.g., `mean`, `minPval`).

- **Imputation**:
  - `params.p_threshold`: Fraction of NaN probes for which a CpG is considered corrupted and removed.
  - `params.s_threshold`: Fraction of NaN samples for which a sample is considered corrupted and removed.
  - `params.imputer_type`: Type of imputation (`mean`, `median`, `knn`).

In case you need additional information on parameters, run the following command:

nextflow run methyl-array-qc.nf --help

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

## Known Issues and TODOs
- Add internal validation for input data (e.g., check sample sheet, count files).
- Generate additional statistics (e.g., PCA, beta distribution, NaN distribution across groups).
- Implement multiprocessing for additional analyses.
