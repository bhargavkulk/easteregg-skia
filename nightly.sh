set -e -x
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

EASTER_CMD="./out/Debug/optimizer --transform easteregg --input ./test.skp --output $EASTER_SKP"
SKRECORDOPT_CMD="./out/Debug/optimizer --transform skrecordopt --input ./test.skp --output $SKRECORDOPT_SKP"
BASELINE_CMD="./out/Debug/optimizer --transform none --input ./test.skp --output $BASELINE_SKP"

$EASTER_CMD
$SKRECORDOPT_CMD
$BASELINE_CMD

./out/Debug/nanobench --sourceType skp --benchType playback --skps "$REPORT_DIR" --config 8888 gl --samples 50
