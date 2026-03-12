#!/usr/bin/env bash
set -e -x

DISPLAY_NUMBER=${DISPLAY_NUMBER:-99}
export DISPLAY=":$DISPLAY_NUMBER"
XORG_PID=""

REPORT_DIR=${REPORT_DIR:-$(pwd)/report}
RENDER_TOOL=${RENDER_TOOL:-renderer_opt}
RENDER_BIN=${RENDER_BIN:-out/Debug/$RENDER_TOOL}

case "$RENDER_TOOL" in
    dm|renderer|renderer_opt) ;;
    *)
        echo "Unsupported RENDER_TOOL: $RENDER_TOOL (expected dm, renderer, or renderer_opt)" >&2
        exit 1
        ;;
esac

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

python3 tools/git-sync-deps

./bin/gn gen out/Debug --args='skia_enable_graphite=true skia_use_vulkan=true cc="clang" cxx="clang++" extra_cflags=["-O3","-flto=thin"] extra_ldflags=["-flto=thin"]'
ninja -C out/Debug optimizer nanobench renderer_opt skp_parser optimizer_stdout

rm -rf opt report
mkdir opt
mkdir report

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp -r jsons report/jsons

./out/Debug/optbench --skps skps/*.skp --stats "report/optbench.json"

start_xorg

python scripts/run_all_skps.py \
       --skp-dir skps/ \
       --optimizer out/Debug/optimizer \
       --nanobench out/Debug/nanobench \
       --opt-dir opt \
       --report-dir "report" \
       --nanobench-dir "report/nanobench" \
       --json-dir jsons/ \
       --samples 100 \
       --renderer out/Debug/renderer_opt \
       --render-tool renderer_opt \
       --png-dir report/pngs \
       --backend grvk

python scripts/altair_report_gen.py \
       --nanobench-dir "report/nanobench" \
       --json-dir jsons \
       --optbench-stats "report/optbench.json" \
       --output "report/index.html" \
       --skp-dir skps/ \
       --optimizer-stdout out/Debug/optimizer_stdout \
       --backend-name Graphite/Vulkan \
       --backend grvk
