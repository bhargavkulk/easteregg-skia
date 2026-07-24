#!/usr/bin/env bash
set -e -x

export GIT_SYNC_DEPS_SKIP_EMSDK=1

if (( $# > 2 )); then
    echo "Usage: $0 [benchmark-folder] [nanobench-runs]" >&2
    exit 1
fi

BENCHMARK_DIR=${1:-bench100}
NANOBENCH_RUNS=${2:-1}
if [[ ! "$NANOBENCH_RUNS" =~ ^[1-9][0-9]*$ ]]; then
    echo "nanobench-runs must be a positive integer: $NANOBENCH_RUNS" >&2
    exit 1
fi

SKP_DIR=${SKP_DIR:-"$BENCHMARK_DIR/skps"}
JSON_DIR=${JSON_DIR:-"$BENCHMARK_DIR/jsons"}
SAMPLES=${SAMPLES:-100}

rm -rf opt report
mkdir -p opt
mkdir -p report/jsons

cp -r "$JSON_DIR"/. report/jsons

GL_CULLMAX=$(./out/Debug/backend_limit --backend gl)
GR_CULLMAX=$(./out/Debug/backend_limit --backend grmtl)
CULLMAX=$GL_CULLMAX
if [ "$GR_CULLMAX" -lt "$CULLMAX" ]; then
    CULLMAX=$GR_CULLMAX
fi

./out/Debug/optbench --skps "$SKP_DIR"/*.skp --stats report/optbench.json

uv run python scripts/gen_passes.py \
    "$SKP_DIR" \
    report/jsons \
    report/passes.json

uv run python scripts/run_measurements.py \
    "$SKP_DIR" \
    report/jsons \
    opt/ganesh \
    report/ganesh \
    --samples "$SAMPLES" \
    --backend gl \
    --cullmax "$CULLMAX" \
    --nanobench-runs "$NANOBENCH_RUNS"

uv run python scripts/run_measurements.py \
    "$SKP_DIR" \
    report/jsons \
    opt/graphite \
    report/graphite \
    --samples "$SAMPLES" \
    --backend grmtl \
    --cullmax "$CULLMAX" \
    --nanobench-runs "$NANOBENCH_RUNS"

PYTHONUNBUFFERED=1 uv run python scripts/collate_data.py report --apple --cullmax "$CULLMAX"
PYTHONUNBUFFERED=1 uv run python scripts/generate_html.py report --platform Apple
