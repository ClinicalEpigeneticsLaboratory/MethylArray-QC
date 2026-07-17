#!/usr/bin/env bash
# Throwaway helper: regenerate poetry.lock and rebuild the python Docker image,
# logging progress with timestamps. Run detached so it survives the terminal /
# Claude Code closing (it still pauses if Windows sleeps the WSL2 VM).
# Safe to delete after the build.

# Self-redirect all output to a fixed log so the detached launch needs no shell
# redirection (which was getting mangled across the Git-Bash -> wsl.exe -> bash layers).
exec > /home/pprzybylowicz/mqc_build.log 2>&1

# Ensure poetry (usually in ~/.local/bin) is on PATH even non-interactively.
[ -f "$HOME/.profile" ] && . "$HOME/.profile" 2>/dev/null
export PATH="$HOME/.local/bin:$PATH"

REPO=/mnt/c/Users/patrycja.przybylowic/Documents/MethylArray-QC/.claude/worktrees/loving-carson-55d411
cd "$REPO" || { echo "CD FAILED: $REPO"; exit 1; }

echo "=== $(date '+%F %T') host=$(hostname) ==="
echo "=== tools: poetry=$(command -v poetry)  docker=$(command -v docker) ==="

echo "=== $(date '+%F %T') STEP 1/2 poetry lock START ==="
poetry lock; rc=$?
echo "=== $(date '+%F %T') poetry lock END rc=$rc ==="
if [ "$rc" -ne 0 ]; then echo "ABORT: poetry lock failed (rc=$rc)"; echo "ALL_DONE BUILD_FAILED"; exit "$rc"; fi

echo "=== $(date '+%F %T') STEP 2/2 docker build START ==="
docker build -f images/Python/Dockerfile -t janbinkowski96/methyl-array-qc-python .
rc=$?
echo "=== $(date '+%F %T') docker build END rc=$rc ==="

if [ "$rc" -eq 0 ]; then echo "ALL_DONE BUILD_SUCCESS"; else echo "ALL_DONE BUILD_FAILED rc=$rc"; fi
