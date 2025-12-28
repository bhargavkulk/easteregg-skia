set -e -x
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
ninja -C out/Debug optimizer nanobench renderer
REPORT_DIR=report
mkdir -p "$REPORT_DIR"
EASTER_SKP="$REPORT_DIR/easteregg.skp"
SKRECORDOPT_SKP="$REPORT_DIR/skrecordopt.skp"
BASELINE_SKP="$REPORT_DIR/no_optimization.skp"
NANOBENCH_JSON="$REPORT_DIR/nanobench.json"
SKP_CLIP="0,0,1280,3160"
EASTER_PNG="$REPORT_DIR/easteregg.png"
SKRECORDOPT_PNG="$REPORT_DIR/skrecordopt.png"
DIFF_PNG="$REPORT_DIR/easteregg_vs_skrecordopt_diff.png"

EASTER_CMD="./out/Debug/optimizer --transform easteregg --input ./test.skp --output $EASTER_SKP"
SKRECORDOPT_CMD="./out/Debug/optimizer --transform skrecordopt --input ./test.skp --output $SKRECORDOPT_SKP"
BASELINE_CMD="./out/Debug/optimizer --transform none --input ./test.skp --output $BASELINE_SKP"

$EASTER_CMD
$SKRECORDOPT_CMD
$BASELINE_CMD

./out/Debug/renderer --input "$EASTER_SKP" --output "$EASTER_PNG"
./out/Debug/renderer --input "$SKRECORDOPT_SKP" --output "$SKRECORDOPT_PNG"

if command -v compare >/dev/null 2>&1; then
    compare "$EASTER_PNG" "$SKRECORDOPT_PNG" "$DIFF_PNG" || true
elif command -v magick >/dev/null 2>&1; then
    magick compare "$EASTER_PNG" "$SKRECORDOPT_PNG" "$DIFF_PNG" || true
else
    echo "ImageMagick compare not found; skipping diff image"
fi

./out/Debug/nanobench --sourceType skp --benchType playback --skps "$REPORT_DIR" --config gl --samples 50 --clip "$SKP_CLIP" --outResultsFile "$NANOBENCH_JSON"
