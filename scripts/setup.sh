#!/bin/sh

convert "Source Files/Logo/Logo.psd[0]" -flatten -layers merge static/images/kleiderbuegel.png

# Favicons
SOURCE="static/images/kleiderbuegel.png" OPTIONS="-resize 128x128 -transparent white" ./themes/projektemacher-base/scripts/favicon.sh


yarn install
yarn svgo
