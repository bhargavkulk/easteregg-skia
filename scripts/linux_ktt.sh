#!/usr/bin/env bash
set -euo pipefail


if [ -z "${DISPLAY:-}" ]; then
    echo "DISPLAY must point to an existing host X server" >&2
    exit 1
fi

if [ -z "${XAUTHORITY:-}" ] || [ ! -r "$XAUTHORITY" ]; then
    echo "XAUTHORITY must point to a readable Xauthority file" >&2
    exit 1
fi

mkdir -p scratch/images

./out/Debug/optimizer \
    --input bench100/skps/pinterest.com__layer_66.skp \
    --output scratch/pinterest.com__layer_66__opt.skp \
    --transform easteregg

./out/Debug/nanobench \
    --sourceType skp \
    --benchType playback \
    --samples 100 \
    --skps bench100/skps/pinterest.com__layer_66.skp scratch/pinterest.com__layer_66__opt.skp \
    --config gl \
    --purgeBetweenBenches \
    --writePath scratch/images \
    --outResultsFile scratch/nanobench.json

compare \
    scratch/images/gl/pinterest.com__layer_66.skp_1.png \
    scratch/images/gl/pinterest.com__layer_66__opt.skp_1.png \
    scratch/pinterest.com__layer_66__diff.png || true
