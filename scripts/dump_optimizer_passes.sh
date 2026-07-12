#!/usr/bin/env bash
# Dumps the intermediate SKPs produced by optimizer_dump_passes for every SKP
# directly contained in an input directory.

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 INPUT_SKP_DIR OUTPUT_DIR" >&2
    exit 1
fi

input_dir=$1
output_dir=$2
optimizer=${OPTIMIZER_DUMP_PASSES:-out/Debug/optimizer_dump_passes}

if [[ ! -d "$input_dir" ]]; then
    echo "Input SKP directory does not exist: $input_dir" >&2
    exit 1
fi

if [[ ! -x "$optimizer" ]]; then
    echo "optimizer_dump_passes is not executable: $optimizer" >&2
    echo "Build it with: ninja -C out/Debug optimizer_dump_passes" >&2
    exit 1
fi

mkdir -p "$output_dir"

found=false
for skp in "$input_dir"/*.skp; do
    [[ -f "$skp" ]] || continue
    found=true
    "$optimizer" --input "$skp" --output_dir "$output_dir"
done

if [[ "$found" == false ]]; then
    echo "No .skp files found in: $input_dir" >&2
    exit 1
fi
