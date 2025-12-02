set -e -x
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++" extra_cflags_cc=["-frtti"]'
ninja -C out/Debug easteregg
./out/Debug/easteregg --input ./test.skp --output ./report/
python3 easteregg/report_generator.py \
    --data ./report/report_data.txt \
    --before ./report/before.png \
    --after ./report/after.png \
    --output ./report/index.html
