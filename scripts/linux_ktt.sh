#!/usr/bin/env bash
set -e

DISPLAY_NUMBER=${DISPLAY_NUMBER:-99}
export DISPLAY=":$DISPLAY_NUMBER"
XORG_PID=""

mkdir -p scratch/images
XORG_LOG=scratch/Xorg-"$DISPLAY_NUMBER".log

stop_xorg() {
    if [ -n "$XORG_PID" ] && kill -0 "$XORG_PID" >/dev/null 2>&1; then
        kill "$XORG_PID" || true
        wait "$XORG_PID" 2>/dev/null || true
    fi
    XORG_PID=""
}

start_xorg() {
    if [ -n "$XORG_PID" ] && kill -0 "$XORG_PID" >/dev/null 2>&1; then
        return
    fi

    Xorg ":$DISPLAY_NUMBER" -noreset >"$XORG_LOG" 2>&1 &
    XORG_PID=$!

    sleep 2
}

trap stop_xorg EXIT

start_xorg

./out/Debug/optimizer \
    --input bench100/skps/pinterest.com__layer_966.skp \
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
