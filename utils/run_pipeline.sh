#!/usr/bin/env bash
# Reusable launcher for MethylArray-QC that prevents the WSL2 + Docker Desktop
# bind-mount failure mode. When Nextflow is launched from inside Docker Desktop's
# bind-mount staging area (/mnt/wsl/docker-desktop-bind-mounts/...), or with the
# work directory on a Windows/WSL mount, per-task containers come up with an empty
# working directory and every process dies with:
#     /bin/bash: .command.sh: No such file or directory
#
# This script:
#   1. refuses to run from Docker Desktop's bind-mount staging area,
#   2. defaults the Nextflow work directory to native ext4 (under $HOME),
#   3. forwards all remaining arguments to `nextflow run main.nf`.
#
# Usage:
#   utils/run_pipeline.sh -params-file examples/params.json -profile docker
#   utils/run_pipeline.sh --input /path/idats --output results/ --sample_sheet ss.csv
#   NXF_WORK=/custom/ext4/path utils/run_pipeline.sh -params-file params.json
set -euo pipefail

STAGING_MARKER='docker-desktop-bind-mounts'

# Physical path of the repo root. `pwd -P` resolves the Docker bind-mount
# reflection, so a bad launch location is detected even when the shell CWD looks
# fine (e.g. reached via a symlink or a mount).
SCRIPT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -P "$SCRIPT_DIR/.." && pwd -P)"

if [[ "$REPO_ROOT" == *"$STAGING_MARKER"* ]]; then
    cat >&2 <<EOF
ERROR: this checkout resolves to Docker Desktop's bind-mount staging area:
  $REPO_ROOT
Per-task containers cannot re-mount this path, so every process would fail with
"/bin/bash: .command.sh: No such file or directory".

Run the pipeline from your real project checkout instead (verify with 'pwd -P';
the path must NOT contain '$STAGING_MARKER') - ideally a copy on native ext4
under \$HOME.
EOF
    exit 1
fi

cd "$REPO_ROOT"

# Respect a work dir the caller passed explicitly (-work-dir / -w); otherwise put
# it on native ext4. On WSL, $HOME is ext4; a work dir on /mnt/c or /mnt/wsl
# frequently breaks container bind-mounts under Docker Desktop.
user_set_workdir=false
for arg in "$@"; do
    case "$arg" in
        -work-dir | -w)
            user_set_workdir=true
            break
            ;;
    esac
done

workdir_args=()
if [[ "$user_set_workdir" == false ]]; then
    if [[ -z "${NXF_WORK:-}" ]]; then
        NXF_WORK="$HOME/nxf_work/$(basename "$REPO_ROOT")"
        echo "NXF_WORK not set; defaulting to ext4 work dir: $NXF_WORK" >&2
    fi
    case "$NXF_WORK" in
        /mnt/*)
            echo "WARNING: NXF_WORK is on a mounted filesystem ($NXF_WORK); under WSL2 +" >&2
            echo "         Docker Desktop this can break container bind-mounts. Prefer \$HOME." >&2
            ;;
    esac
    mkdir -p "$NXF_WORK"
    export NXF_WORK
    workdir_args=(-work-dir "$NXF_WORK")
fi

echo "Launching: nextflow run main.nf ${workdir_args[*]:-} $*" >&2
exec nextflow run main.nf "${workdir_args[@]}" "$@"
