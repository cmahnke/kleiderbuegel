#!/bin/sh

./scripts/cleanup-index.sh

./themes/projektemacher-base/scripts/cleanup.sh
rm -rf static/images/background.jpg
find content/post/ -name front.svg  -o -name top.svg -o -name back.svg -exec rm {} \;