#!/usr/bin/env bash
# Downloads 15 EPIC IDAT files from GEO series GSE86831
# (Pidsley et al. 2016, Genome Biology - EPIC array validation study)
# Requirements: wget or curl, tar, gunzip
#
# Run from the repository root:
#   bash examples/fetch_example_data.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IDAT_DIR="${SCRIPT_DIR}/idats"
GEO_SERIES="GSE86831"
GEO_FTP="ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE86nnn/${GEO_SERIES}/suppl"
TARFILE="${GEO_SERIES}_RAW.tar"
EXPECTED_IDAT_COUNT=30  # 15 samples x 2 channels (Grn + Red)

mkdir -p "${IDAT_DIR}"

# Download RAW tar if not already present
if [[ ! -f "${IDAT_DIR}/${TARFILE}" ]]; then
    echo "Downloading ${TARFILE} from NCBI GEO FTP (~373 MB)..."
    if command -v wget &>/dev/null; then
        wget -q --show-progress -P "${IDAT_DIR}" "${GEO_FTP}/${TARFILE}"
    elif command -v curl &>/dev/null; then
        curl -L --progress-bar -o "${IDAT_DIR}/${TARFILE}" "${GEO_FTP}/${TARFILE}"
    else
        echo "ERROR: neither wget nor curl found. Please install one and retry."
        exit 1
    fi
else
    echo "Archive ${TARFILE} already downloaded, skipping."
fi

# Check whether extraction + renaming has already been completed.
# Verify both the total count AND the absence of any unrenamed GSM-prefixed files
# to guard against a partial run that was interrupted mid-rename.
IDAT_COUNT=$(find "${IDAT_DIR}" -maxdepth 1 -name "*.idat" | wc -l | tr -d ' ')
GSM_COUNT=$(find "${IDAT_DIR}" -maxdepth 1 -name "GSM*.idat" | wc -l | tr -d ' ')
if [[ "${IDAT_COUNT}" -eq "${EXPECTED_IDAT_COUNT}" && "${GSM_COUNT}" -eq 0 ]]; then
    echo "IDAT files already extracted and renamed (${IDAT_COUNT} found), skipping."
else
    echo "Extracting IDAT files..."
    tar -xf "${IDAT_DIR}/${TARFILE}" -C "${IDAT_DIR}"

    echo "Decompressing IDAT files..."
    find "${IDAT_DIR}" -name "*.idat.gz" -exec gunzip -f {} \;

    # GEO names files as {GSM_ID}_{SentrixID}_{Position}_{Color}.idat
    # The pipeline expects {SentrixID}_{Position}_{Color}.idat — strip the GSM prefix
    echo "Renaming files to pipeline format ({SentrixID}_{Position}_{Color}.idat)..."
    for f in "${IDAT_DIR}"/GSM*.idat; do
        [[ -f "$f" ]] || continue
        filename="$(basename "$f")"
        # Strip leading GSM number and underscore (e.g. "GSM2309170_" prefix)
        new_name="$(echo "${filename}" | sed 's/^GSM[0-9]*_//')"
        if [[ "${filename}" != "${new_name}" ]]; then
            mv "${f}" "${IDAT_DIR}/${new_name}"
        fi
    done

    IDAT_COUNT=$(find "${IDAT_DIR}" -maxdepth 1 -name "*.idat" | wc -l | tr -d ' ')
    echo "Found ${IDAT_COUNT} IDAT files (expected ${EXPECTED_IDAT_COUNT}: 15 samples x 2 channels)"

    if [[ "${IDAT_COUNT}" -ne "${EXPECTED_IDAT_COUNT}" ]]; then
        echo "ERROR: unexpected IDAT file count (${IDAT_COUNT}). Check ${IDAT_DIR}."
        exit 1
    fi
fi

echo ""
echo "Done. To run the pipeline (from the repository root):"
echo "  nextflow run main.nf -params-file examples/params.json"
echo "  # or"
echo "  make run_example"
