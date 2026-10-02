#!/bin/sh
# Vendor VersaTiles style + sprites for offline/self-hosted maps.
#
# Outputs (new files only):
#   static/map-styles/sprites/{base,extras,icons}{,@2x}.{png,json}
#   static/map-styles/sprite{,@2x}.{png,json}   (legacy alias of `base`,
#     because the theme expects /map-styles/sprite)
#   static/map-styles/kleiderbuegel-colorful.json (via generate script)
#
# Env overrides:
#   SKIP_VERSATILES=1 ......... skip everything (also honored by setup.sh)
#   VERSATILES_STYLE_VERSION .. release tag for sprites.tar.gz (default 6.0.3,
#                               must match @versatiles/style in package.json)
#   VERSATILES_SPRITES_URL .... full URL override for sprites.tar.gz

set -e

if [ -n "$SKIP_VERSATILES" ] ; then
    echo "Skipping VersaTiles style+sprites (SKIP_VERSATILES is set)"
    exit 0
fi

VERSION="${VERSATILES_STYLE_VERSION:-6.0.3}"
SPRITES_URL="${VERSATILES_SPRITES_URL:-https://github.com/versatiles-org/versatiles-style/releases/download/v${VERSION}/sprites.tar.gz}"
DEST="static/map-styles/sprites"

mkdir -p "$DEST"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT INT TERM
TARBALL="$TMPDIR/sprites.tar.gz"

echo "Downloading VersaTiles sprites v${VERSION}"
if command -v curl >/dev/null 2>&1 ; then
    curl -sSL "$SPRITES_URL" -o "$TARBALL"
elif command -v wget >/dev/null 2>&1 ; then
    wget -q -O "$TARBALL" "$SPRITES_URL"
else
    echo "Need curl or wget to download $SPRITES_URL" >&2
    exit 1
fi

tar -xzf "$TARBALL" -C "$DEST"

# Legacy single-sprite path expected by the theme (/map-styles/sprite):
# plain copies of the `base` sheet (cp, not symlink, for Hugo/static + git).
for SUFFIX in "" "@2x" ; do
    cp -f "$DEST/base${SUFFIX}.png" "static/map-styles/sprite${SUFFIX}.png"
    cp -f "$DEST/base${SUFFIX}.json" "static/map-styles/sprite${SUFFIX}.json"
done

node scripts/generate-versatiles-style.mjs

echo "VersaTiles style + sprites ready in static/map-styles/"
