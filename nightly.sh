set -e -x
python3 tools/git-sync-deps
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++"'
ninja -C out/Debug easteregg
