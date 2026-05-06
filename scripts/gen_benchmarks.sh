#!/usr/bin/env bash
set -e -x

if [[ ! -e "$1" ]]; then
    echo "$1 does not exist"
    exit 1
fi

if [[ ! -f "$1" ]]; then
    echo "$1 is not a file"
    exit 1
fi

uv run scripts/download_skps.py "$1" "$2"
uv run scripts/skps_to_jsons.py "$2/skps/" "$2/jsons/"
uv run scripts/move_nosl_skps.py \
   "$2/skps" \
   "$2/jsons" \
   "$2/skps_nosl" \
   "$2/jsons_nosl" \
   "$2/summary.txt"
