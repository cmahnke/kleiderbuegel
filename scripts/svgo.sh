#!/usr/bin/env bash

IMAGES=$(find "Source Files" -name '*.svg') ./themes/projektemacher-base/scripts/svgo.sh
cp "Source Files/Other/geomarker.svg" static/images
