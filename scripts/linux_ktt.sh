#!/usr/bin/env bash
set -e

mkdir -p scratch/images

./out/Debug/optimizer \
    --input bench100/skps/pinterest.com__layer_97.skp \
    --output scratch/pinterest.com__layer_97__opt.skp \
    --transform easteregg

./out/Debug/nanobench \
    --sourceType skp \
    --benchType playback \
    --samples 100 \
    --skps bench100/skps/pinterest.com__layer_97.skp scratch/pinterest.com__layer_97__opt.skp \
    --config gl \
    --purgeBetweenBenches \
    --writePath scratch/images \
    --outResultsFile scratch/nanobench.json

compare \
    scratch/images/gl/pinterest.com__layer_97.skp_1.png \
    scratch/images/gl/pinterest.com__layer_97__opt.skp_1.png \
    scratch/pinterest.com__layer_97__diff.png || true
