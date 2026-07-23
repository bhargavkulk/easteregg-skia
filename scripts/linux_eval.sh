#!/usr/bin/env bash
set -euo pipefail

if [[ $# -gt 1 ]]; then
    echo "usage: $0 [nanobench-runs]" >&2
    exit 2
fi

nanobench_runs=${1:-25}
if ! [[ "$nanobench_runs" =~ ^[1-9][0-9]*$ ]]; then
    echo "nanobench-runs must be a positive integer" >&2
    exit 2
fi

if [ -z "${DISPLAY:-}" ]; then
    echo "DISPLAY must point to an existing host X server" >&2
    exit 1
fi

if [ -z "${XAUTHORITY:-}" ] || [ ! -r "$XAUTHORITY" ]; then
    echo "XAUTHORITY must point to a readable Xauthority file" >&2
    exit 1
fi

rm -rf artifacts/opt artifacts/report
mkdir -p artifacts/opt artifacts/report/jsons
cp -a bench100/jsons/. artifacts/report/jsons/

GL_CULLMAX=$(./out/Debug/backend_limit --backend gl)
GR_CULLMAX=$(./out/Debug/backend_limit --backend grvk)
CULLMAX=$GL_CULLMAX
if [ "$GR_CULLMAX" -lt "$CULLMAX" ]; then
    CULLMAX=$GR_CULLMAX
fi

./out/Debug/optbench \
    --skps bench100/skps/*.skp \
    --stats artifacts/report/optbench.json

uv run python scripts/gen_passes.py \
    bench100/skps \
    artifacts/report/jsons \
    artifacts/report/passes.json

uv run python scripts/run_measurements.py \
    bench100/skps \
    artifacts/report/jsons \
    artifacts/opt/ganesh \
    artifacts/report/ganesh \
    --samples 100 \
    --nanobench-runs "$nanobench_runs" \
    --backend gl \
    --cullmax "$CULLMAX"

uv run python scripts/run_measurements.py \
    bench100/skps \
    artifacts/report/jsons \
    artifacts/opt/graphite \
    artifacts/report/graphite \
    --samples 100 \
    --nanobench-runs "$nanobench_runs" \
    --backend grvk \
    --cullmax "$CULLMAX"

uv run python scripts/collate_data.py artifacts/report --cullmax "$CULLMAX"
uv run python scripts/generate_html.py artifacts/report --platform Linux
