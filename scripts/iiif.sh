#!/usr/bin/env bash

IMAGES=$(find content -maxdepth 4 -name '*.png' -not -name 'ogPreview.png') ./themes/projektemacher-base/scripts/iiif.sh
