#!/usr/bin/env bash
set -e -x

REPORT_DIR=${REPORT_DIR:-$(pwd)/report}

mkdir -p "$REPORT_DIR"

# trap stop_xorg EXIT

if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi

#./bin/gn gen out/Debug --args='skia_enable_graphite=true skia_use_metal=true cc="clang" cxx="clang++" extra_cflags=["-O3","-flto=thin"] extra_ldflags=["-flto=thin"]'
#ninja -C out/Debug optimizer nanobench "$RENDER_TOOL" optimizer_stdout

rm -rf opt report
mkdir opt
mkdir report

cp -r old_jsons report/jsons

./out/Debug/optbench --skps skps200/*.skp --stats "report/optbench.json"

uv run python scripts/run_all_skps.py \
       --skp-dir skps200/ \
       --optimizer out/Debug/optimizer \
       --nanobench out/Debug/nanobench \
       --opt-dir opt \
       --report-dir "report" \
       --nanobench-dir "report/nanobench" \
       --json-dir jsons200/ \
       --samples 100 \
       --renderer out/Debug/renderer_opt \
       --render-tool renderer_opt \
       --png-dir report/pngs \
       --backend grmtl

uv run python scripts/report_gen.py \
       --nanobench-dir "report/nanobench" \
       --json-dir jsons200/ \
       --optbench-stats "report/optbench.json" \
       --output "report/index.html" \
       --skp-dir skps200/ \
       --optimizer-stdout out/Debug/optimizer_stdout \
       --backend-name graphite-metal \
       --backend grmtl
