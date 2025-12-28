set -e -x

DISPLAY_NUMBER=${DISPLAY_NUMBER:-99}
export DISPLAY=":$DISPLAY_NUMBER"
XORG_PID=""

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
    Xorg ":$DISPLAY_NUMBER" >"$XORG_LOG" 2>&1 &
    XORG_PID=$!
    sleep 2
}

trap stop_xorg EXIT
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
XORG_LOG=${XORG_LOG:-$REPORT_DIR/Xorg-$DISPLAY_NUMBER.log}
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
ninja -C out/Debug optimizer nanobench renderer skp_parser print_bounds

python3 -m venv .venv/

rm -rf report # skps jsons benchmarks.json
mkdir report

if [ ! -d "skps" ]; then
    $(pwd)/.venv/bin/python -m pip install uv
    $(pwd)/.venv/bin/python -m uv sync --no-dev
    $(pwd)/.venv/bin/python -m playwright install
    $(pwd)/.venv/bin/python scripts/download_skps.py urls.toml skps/
    $(pwd)/.venv/bin/python scripts/skp_to_json.py skps/ jsons/ ./out/Debug/skp_parser
    $(pwd)/.venv/bin/python scripts/benchmark_gen.py skps/ jsons/ benchmarks.json ./out/Debug/print_bounds
fi

cp -r jsons report/jsons
cp -r benchmarks.json report/

rm -rf opt
mkdir opt

./out/Debug/optimizer --input skps/Zen_News__layer_2.skp --output opt/Zen_News__layer_2_ee.skp
./out/Debug/optimizer --input skps/Zen_News__layer_2.skp --output opt/Zen_News__layer_2_sk.skp --transform skrecordopt

cp skps/Zen_News__layer_2.skp report/
cp opt/Zen_News__layer_2_ee.skp report/
cp opt/Zen_News__layer_2_sk.skp report/


# start_xorg
# ./out/Debug/nanobench --sourceType skp --benchType playback --samples 50 --skps skps/Zen_News__layer_2.skp opt/Zen_News__layer_2_ee.skp opt/Zen_News__layer_2_sk.skp --samples 100 --clip 0,0,1216,1733 --outResultsFile report/nanobench.json
# stop_xorg
