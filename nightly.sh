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
    # Give Xorg a moment to come up before any GL clients connect.
    sleep 2
}

trap stop_xorg EXIT
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
ninja -C out/Debug optimizer nanobench
REPORT_DIR=report
mkdir -p "$REPORT_DIR"
EASTER_SKP="$REPORT_DIR/easteregg.skp"
SKRECORDOPT_SKP="$REPORT_DIR/skrecordopt.skp"
BASELINE_SKP="$REPORT_DIR/no_optimization.skp"
NANOBENCH_JSON="$REPORT_DIR/nanobench.json"
XORG_LOG=${XORG_LOG:-$REPORT_DIR/Xorg-$DISPLAY_NUMBER.log}

EASTER_CMD="./out/Debug/optimizer --transform easteregg --input ./test.skp --output $EASTER_SKP"
SKRECORDOPT_CMD="./out/Debug/optimizer --transform skrecordopt --input ./test.skp --output $SKRECORDOPT_SKP"
BASELINE_CMD="./out/Debug/optimizer --transform none --input ./test.skp --output $BASELINE_SKP"

$EASTER_CMD
$SKRECORDOPT_CMD
$BASELINE_CMD

start_xorg
./out/Debug/nanobench --sourceType skp --benchType playback --skps "$REPORT_DIR" --config 8888 gl --samples 50 --outResultsFile "$NANOBENCH_JSON"
stop_xorg
