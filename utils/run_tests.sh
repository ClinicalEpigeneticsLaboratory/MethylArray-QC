#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$REPO_ROOT/logs"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/test_run_${TIMESTAMP}.log"

mkdir -p "$LOG_DIR"

# Redirect all output to log file AND terminal
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
separator() { echo ""; echo "========================================"; echo "$1"; echo "========================================"; }

PASS=0
FAIL=0
declare -a FAILURES

run_step() {
    local step_name="$1"
    shift
    separator "STEP: $step_name"
    log "Running: $*"
    if "$@"; then
        log "PASS: $step_name"
        ((PASS++)) || true
    else
        log "FAIL: $step_name (exit code $?)"
        ((FAIL++)) || true
        FAILURES+=("$step_name")
    fi
}

cd "$REPO_ROOT"
log "Test run started. Log: $LOG_FILE"
log "Working directory: $REPO_ROOT"

# 1. Smoke-test the config
run_step "Smoke-test config (nf-test list)" \
    nf-test list

# 2. Generate/update snapshot baselines (stub mode)
run_step "Update snapshots (stub mode)" \
    nf-test test --update-snapshot

# 3. Confirm snapshots are locked
run_step "Confirm snapshots locked" \
    nf-test test

# 4. Validator error-state tests (real containers)
#    Uncomment error blocks in the test files before enabling this step.
# run_step "Validator error-state tests (real containers)" \
#     nf-test test \
#       tests/modules.additional_validators_init.nf.test \
#       tests/modules.additional_validators_after_impute.nf.test \
#       --verbose

separator "SUMMARY"
log "Passed : $PASS"
log "Failed : $FAIL"
if [[ ${#FAILURES[@]} -gt 0 ]]; then
    log "Failed steps:"
    for f in "${FAILURES[@]}"; do
        log "  - $f"
    done
    log "OVERALL: FAILED"
    exit 1
else
    log "OVERALL: ALL PASSED"
fi
# how to run: nohup utils/run_tests.sh > "test_logs/test_res_$(date +"%Y_%m_%d_%I_%M_%p").log" 2>&1 &