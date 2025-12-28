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

$(pwd)/.venv/bin/python -m pip install uv
$(pwd)/.venv/bin/python -m uv sync
