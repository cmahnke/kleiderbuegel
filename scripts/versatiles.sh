#!/bin/sh
# Generates the self-hosted VersaTiles style for this site.
# The map sprites are vendored separately by the theme's
# scripts/init/get-map-styles.sh (run via setup.sh).
#
# Output (new files only, never overwrites tracked code):
#   static/map-styles/kleiderbuegel-colorful.json (via generate script)
#
# Env overrides:
#   SKIP_VERSATILES=1 ......... skip everything (also honored by setup.sh)

set -e

if [ -n "$SKIP_VERSATILES" ] ; then
    echo "Skipping VersaTiles style (SKIP_VERSATILES is set)"
    exit 0
fi

node scripts/generate-versatiles-style.mjs

echo "VersaTiles style ready in static/map-styles/"
