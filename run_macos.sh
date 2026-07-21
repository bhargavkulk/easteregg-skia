#!/usr/bin/env bash
set -e -x

export GIT_SYNC_DEPS_SKIP_EMSDK=1

SKP_DIR=${SKP_DIR:-bench100/skps}
JSON_DIR=${JSON_DIR:-bench100/jsons}
SAMPLES=${SAMPLES:-100}


# if [ ! -d "out/Debug" ]; then
python3 tools/git-sync-deps
# fi

./bin/gn gen out/Debug --args='target_cpu="arm64" skia_enable_graphite=true skia_use_metal=true cc="clang" cxx="clang++" extra_cflags=["-O3","-flto=thin"] extra_ldflags=["-flto=thin"]'
ninja -C out/Debug optimizer nanobench renderer_opt optimizer_stdout optbench backend_limit

python3 -m venv venv
venv/bin/python -m pip install -r req.txt

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

venv/bin/python scripts/gen_passes.py \
    "$SKP_DIR" \
    report/jsons \
    report/passes.json

venv/bin/python scripts/run_measurements.py \
    "$SKP_DIR" \
    report/jsons \
    opt/ganesh \
    report/ganesh \
    --samples "$SAMPLES" \
    --backend gl \
    --cullmax "$CULLMAX" \
    --nanobench-runs 1

venv/bin/python scripts/run_measurements.py \
    "$SKP_DIR" \
    report/jsons \
    opt/graphite \
    report/graphite \
    --samples "$SAMPLES" \
    --backend grmtl \
    --cullmax "$CULLMAX" \
    --nanobench-runs 1

PYTHONUNBUFFERED=1 venv/bin/python scripts/collate_data.py report --apple --cullmax "$CULLMAX"
PYTHONUNBUFFERED=1 venv/bin/python scripts/generate_html.py report --platform Apple
