#!/usr/bin/env bash
set -e -x

DISPLAY_NUMBER=${DISPLAY_NUMBER:-99}
export DISPLAY=":$DISPLAY_NUMBER"
XORG_PID=""

REPORT_DIR=${REPORT_DIR:-$(pwd)/report}
mkdir -p "$REPORT_DIR"
XORG_LOG=${XORG_LOG:-$REPORT_DIR/Xorg-$DISPLAY_NUMBER.log}

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

if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi

./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
ninja -C out/Debug optimizer nanobench renderer skp_parser print_bounds

python3 -m venv .venv

rm -rf "$REPORT_DIR"
mkdir -p "$REPORT_DIR"

if [ ! -d "skps" ]; then
    $(pwd)/.venv/bin/python -m pip install uv
    $(pwd)/.venv/bin/python -m uv sync --no-dev
    $(pwd)/.venv/bin/python -m playwright install
    $(pwd)/.venv/bin/python scripts/download_skps.py urls.toml skps/
    $(pwd)/.venv/bin/python scripts/skp_to_json.py skps/ jsons/ ./out/Debug/skp_parser
    $(pwd)/.venv/bin/python scripts/benchmark_gen.py skps/ jsons/ benchmarks.json ./out/Debug/print_bounds
fi

cp -r jsons "$REPORT_DIR/jsons"
cp benchmarks.json "$REPORT_DIR/"

rm -rf opt
mkdir opt

start_xorg

$(pwd)/.venv/bin/python scripts/run_all_skps.py \
    --skp-dir skps \
    --optimizer out/Debug/optimizer \
    --nanobench out/Debug/nanobench \
    --opt-dir opt \
    --report-dir "$REPORT_DIR" \
    --nanobench-dir "$REPORT_DIR/nanobench" \
    --json-dir jsons \
    --samples 100

AMAZON_STEM="Amazon__layer_5"
EE_SKP="opt/${AMAZON_STEM}_ee.skp"
SK_SKP="opt/${AMAZON_STEM}_sk.skp"
EE_PNG="$REPORT_DIR/${AMAZON_STEM}_ee.png"
SK_PNG="$REPORT_DIR/${AMAZON_STEM}_sk.png"
DIFF_PNG="$REPORT_DIR/${AMAZON_STEM}_diff.png"

./out/Debug/renderer --input "$EE_SKP" --output "$EE_PNG"
./out/Debug/renderer --input "$SK_SKP" --output "$SK_PNG"

COMPARE_OUTPUT=""
compare -metric MAE "$EE_PNG" "$SK_PNG" "$DIFF_PNG" 2>&1 || true

ls report/nanobench

$(pwd)/.venv/bin/python scripts/report_gen.py \
    --nanobench-dir "$REPORT_DIR/nanobench" \
    --json-dir jsons \
    --output "$REPORT_DIR/index.html"
