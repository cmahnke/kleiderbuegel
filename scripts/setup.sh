#!/bin/sh

convert "Source Files/Logo/Logo.psd[0]" -flatten -layers merge static/images/kleiderbuegel.png

# Generate Previews
python3 ./themes/projektemacher-base/scripts/preview.py
#inkscape preview.svg --export-filename=preview.png
find content -name preview.svg -print -exec bash -c 'inkscape "{}" --export-filename=$(dirname "{}")/$(basename -s .svg "{}").png' \;

# Favicons
SOURCE="static/images/kleiderbuegel.png" OPTIONS="-resize 128x128 -transparent white" ./themes/projektemacher-base/scripts/favicon.sh

yarn install
yarn svgo
