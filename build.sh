#!/usr/bin/env bash
set -e -x

export GIT_SYNC_DEPS_SKIP_EMSDK=1

if [ ! -d "out/Debug" ]; then
    python3 tools/git-sync-deps
fi

./bin/gn gen out/Debug --args='target_cpu="arm64" skia_enable_graphite=true skia_use_metal=true cc="clang" cxx="clang++" extra_cflags=["-O3","-flto=thin"] extra_ldflags=["-flto=thin"]'
ninja -C out/Debug optimizer nanobench renderer_opt optimizer_stdout optbench backend_limit
