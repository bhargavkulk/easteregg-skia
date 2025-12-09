set -e -x
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
ninja -C out/Debug optimizer renderer

REPORT_DIR=./report
mkdir -p "$REPORT_DIR"
EASTER_SKP="$REPORT_DIR/easteregg.skp"
SKRECORDOPT_SKP="$REPORT_DIR/skrecordopt.skp"
BASELINE_SKP="$REPORT_DIR/no_optimization.skp"
RENDERED_EASTER="$REPORT_DIR/easteregg.png"
RENDERED_SKRECORDOPT="$REPORT_DIR/skrecordopt.png"
RENDERED_BASELINE="$REPORT_DIR/no_optimization.png"

EASTER_CMD="./out/Debug/optimizer --transform easteregg --input ./test.skp --output $EASTER_SKP"
SKRECORDOPT_CMD="./out/Debug/optimizer --transform skrecordopt --input ./test.skp --output $SKRECORDOPT_SKP"
BASELINE_CMD="./out/Debug/optimizer --transform none --input ./test.skp --output $BASELINE_SKP"
RENDER_EASTER_CMD="./out/Debug/renderer --input $EASTER_SKP --output $RENDERED_EASTER"
RENDER_SKRECORDOPT_CMD="./out/Debug/renderer --input $SKRECORDOPT_SKP --output $RENDERED_SKRECORDOPT"
RENDER_BASELINE_CMD="./out/Debug/renderer --input $BASELINE_SKP --output $RENDERED_BASELINE"

hyperfine --shell=none --warmup 2 --runs 10 \
    "$EASTER_CMD" \
    "$SKRECORDOPT_CMD" \
    "$BASELINE_CMD"

hyperfine --shell=none --warmup 2 --runs 10 \
    "$RENDER_EASTER_CMD" \
    "$RENDER_SKRECORDOPT_CMD" \
    "$RENDER_BASELINE_CMD"
