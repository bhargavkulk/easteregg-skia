set -e -x
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti", "-pg"]'
ninja -C out/Debug easteregg

REPORT_DIR=./report
EASTER_DIR="$REPORT_DIR/easteregg"
SKRECORDOPT_DIR="$REPORT_DIR/skrecordopt"
mkdir -p "$EASTER_DIR" "$SKRECORDOPT_DIR"

./out/Debug/easteregg --transform easteregg --input ./test.skp --output "$EASTER_DIR"
./out/Debug/easteregg --transform skrecordopt --input ./test.skp --output "$SKRECORDOPT_DIR"
