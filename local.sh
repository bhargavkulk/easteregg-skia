#!/usr/bin/env bash
set -e -x

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

# trap stop_xorg EXIT

if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi

./bin/gn gen out/Debug --args='skia_enable_graphite=true skia_use_metal=true cc="clang" cxx="clang++" extra_cflags=["-O3","-flto=thin"] extra_ldflags=["-flto=thin"]'
ninja -C out/Debug optimizer nanobench "$RENDER_TOOL" optimizer_stdout

rm -rf opt report
mkdir opt
mkdir report

cp -r old_jsons report/jsons

./out/Debug/optbench --skps old_bench/*.skp --stats "report/optbench.json"

uv run python scripts/run_all_skps.py \
       --skp-dir old_bench \
       --optimizer out/Debug/optimizer \
       --nanobench out/Debug/nanobench \
       --opt-dir opt \
       --report-dir "report" \
       --nanobench-dir "report/nanobench" \
       --json-dir old_jsons \
       --samples 100 \
       --renderer "$RENDER_BIN" \
       --render-tool "$RENDER_TOOL" \
       --png-dir report/pngs \
       --backend grmtl

uv run python scripts/report_gen.py \
       --nanobench-dir "report/nanobench" \
       --json-dir old_jsons \
       --optbench-stats "report/optbench.json" \
       --output "report/index.html" \
       --skp-dir old_bench/ \
       --optimizer-stdout out/Debug/optimizer_stdout \
       --backend grmtl
