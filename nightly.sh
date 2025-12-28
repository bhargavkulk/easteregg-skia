# set -e -x

# DISPLAY_NUMBER=${DISPLAY_NUMBER:-99}
# export DISPLAY=":$DISPLAY_NUMBER"
# XORG_PID=""

# stop_xorg() {
#     if [ -n "$XORG_PID" ] && kill -0 "$XORG_PID" >/dev/null 2>&1; then
#         kill "$XORG_PID" || true
#         wait "$XORG_PID" 2>/dev/null || true
#     fi
#     XORG_PID=""
# }

# start_xorg() {
#     if [ -n "$XORG_PID" ] && kill -0 "$XORG_PID" >/dev/null 2>&1; then
#         return
#     fi
#     Xorg ":$DISPLAY_NUMBER" >"$XORG_LOG" 2>&1 &
#     XORG_PID=$!
#     sleep 2
# }

# trap stop_xorg EXIT
# if [ ! -d "out/Debug" ]; then
#     python3 tools/git-sync-deps
# fi
# XORG_LOG=${XORG_LOG:-$REPORT_DIR/Xorg-$DISPLAY_NUMBER.log}
# ./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
# ninja -C out/Debug optimizer nanobench renderer skp_parser print_bounds

# python3 -m venv .venv/

# rm -rf report # skps jsons benchmarks.json
# mkdir report

# if [ ! -d "skps" ]; then
#     $(pwd)/.venv/bin/python -m pip install uv
#     $(pwd)/.venv/bin/python -m uv sync --no-dev
#     $(pwd)/.venv/bin/python -m playwright install
#     $(pwd)/.venv/bin/python scripts/download_skps.py urls.toml skps/
#     $(pwd)/.venv/bin/python scripts/skp_to_json.py skps/ jsons/ ./out/Debug/skp_parser
#     $(pwd)/.venv/bin/python scripts/benchmark_gen.py skps/ jsons/ benchmarks.json ./out/Debug/print_bounds
# fi

# cp -r jsons report/jsons
# cp -r benchmarks.json report/

# rm -rf opt
# mkdir opt

# ./out/Debug/optimizer --input skps/Zen_News__layer_2.skp --output opt/Zen_News__layer_2_ee.skp
# ./out/Debug/optimizer --input skps/Zen_News__layer_2.skp --output opt/Zen_News__layer_2_sk.skp --transform skrecordopt

# cp skps/Zen_News__layer_2.skp report/
# cp opt/Zen_News__layer_2_ee.skp report/
# cp opt/Zen_News__layer_2_sk.skp report/


# # start_xorg
# # ./out/Debug/nanobench --sourceType skp --benchType playback --samples 50 --skps Zen_News__layer_2.skp Zen_News__layer_2_ee.skp Zen_News__layer_2_sk.skp --config gl --samples 100 --clip 0,0,1216,1733 --outResultsFile report/nanobench.json
# # stop_xorg


#!/usr/bin/env bash
set -euo pipefail
set -x

# MUST be non-root
if [[ "$(id -u)" -eq 0 ]]; then
    echo "ERROR: Do not run this as root"
    exit 1
fi

DISPLAY_NUMBER=99
export DISPLAY=":$DISPLAY_NUMBER"

LOGDIR="$(pwd)/xorg-debug"
LOGFILE="$LOGDIR/Xorg-$DISPLAY_NUMBER.log"
PID=""

mkdir -p "$LOGDIR"

cleanup() {
    if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" || true
        wait "$PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT

echo "Starting Xorg on $DISPLAY as user $(whoami)"
Xorg ":$DISPLAY_NUMBER" -noreset -logfile "$LOGFILE" >"$LOGFILE" 2>&1 &
PID=$!

# wait up to 8s
for i in {1..8}; do
    sleep 1
    if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        echo "Xorg is UP (pid=$PID)"
        break
    fi
done

if ! xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
    echo "Xorg FAILED"
    echo "==== Xorg log ===="
    sed -n '1,200p' "$LOGFILE"
    exit 1
fi

echo "==== xdpyinfo ===="
xdpyinfo -display "$DISPLAY" | head -n 20

echo "==== basic X test ===="
xset q

echo "SUCCESS: Xorg works as non-root"
