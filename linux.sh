#!/usr/bin/env bash
set -e -x

export PATH="$PATH:/home/nightlies/.local/bin"
export GIT_SYNC_DEPS_SKIP_EMSDK=1

DISPLAY_NUMBER=${DISPLAY_NUMBER:-99}
export DISPLAY=":$DISPLAY_NUMBER"
XORG_PID=""

SKP_DIR=${SKP_DIR:-benchnext100/skps}
JSON_DIR=${JSON_DIR:-benchnext100/jsons}
SAMPLES=${SAMPLES:-100}

XORG_LOG=${XORG_LOG:-report/Xorg-$DISPLAY_NUMBER.log}

stop_xorg() {
    if [ -n "$XORG_PID" ] && kill -0 "$XORG_PID" >/dev/null 2>&1; then
        kill "$XORG_PID" || true
        wait "$XORG_PID" 2>/dev/null || true
    fi
    XORG_PID=""
}

start_xorg() {
    if [ -n "$XORG_PID" ] && kill -0 "$XORG_PID" >/dev/null 2>&1; then
        return
    fi

    Xorg ":$DISPLAY_NUMBER" -noreset >"$XORG_LOG" 2>&1 &
    XORG_PID=$!

    sleep 2
}

trap stop_xorg EXIT

#if [ ! -d "out/Debug" ]; then
#    python3 tools/git-sync-deps
#fi

./bin/gn gen out/Debug --args='skia_enable_graphite=true skia_use_vulkan=true cc="clang" cxx="clang++" extra_cflags=["-O3","-flto=thin"] extra_ldflags=["-flto=thin"]'
#ninja -C out/Debug optimizer nanobench renderer_opt skp_parser \
#      optimizer_stdout backend_limit print_bounds
ninja -C out/Debug optimizer nanobench renderer_opt optimizer_stdout optbench backend_limit
rm -rf opt report
mkdir -p opt
mkdir -p report/jsons

cp -r "$JSON_DIR"/. report/jsons

start_xorg

GL_CULLMAX=$(./out/Debug/backend_limit --backend gl)
GR_CULLMAX=$(./out/Debug/backend_limit --backend grvk)
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
    --cullmax "$CULLMAX"

uv run python scripts/run_measurements.py \
    "$SKP_DIR" \
    report/jsons \
    opt/graphite \
    report/graphite \
    --samples "$SAMPLES" \
    --backend grvk \
    --cullmax "$CULLMAX"

uv run python scripts/collate_data.py report --cullmax "$CULLMAX"
uv run python scripts/generate_html.py report --platform Linux
