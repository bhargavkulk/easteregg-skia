set -e -x
if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi
./bin/gn gen out/Debug --args='cc="clang" cxx="clang++"'
ninja -C out/Debug easteregg
