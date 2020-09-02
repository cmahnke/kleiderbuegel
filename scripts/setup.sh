#!/bin/sh

convert "Source Files/Logo/Logo.psd[0]" -flatten -layers merge static/images/kleiderbuegel.png

# Favicons
# See https://gist.github.com/pfig/1808188
convert static/images/kleiderbuegel.png -resize 128x128 -transparent white static/images/favicon-128.png
convert static/images/favicon-128.png -resize 16x16 static/images/favicon-16.png
convert static/images/favicon-128.png -resize 32x32 static/images/favicon-32.png
convert static/images/favicon-128.png -resize 64x64 static/images/favicon-64.png
convert static/images/favicon-16.png static/images/favicon-32.png static/images/favicon-64.png static/images/favicon-128.png -colors 256 static/images/favicon.ico

yarn install
yarn svgo
