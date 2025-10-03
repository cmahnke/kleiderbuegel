#!/bin/sh

set -e

if [ -z "$DEPENDENCY_MANAGER" ] ; then
  DEPENDENCY_MANAGER=npm
fi

# IIIF tiles
echo "Set SKIP_IIIF to something to disable generation of IIIF derivates"

if [ -z "$SKIP_IIIF" ] ; then
    ./scripts/iiif.sh
fi

convert "Source Files/Logo/Logo.psd[0]" -flatten -layers merge static/images/kleiderbuegel.png

# Generate Previews
./themes/projektemacher-base/scripts/preview.sh

#NPM dependencies
echo "Calling theme scripts"
for SCRIPT in $PWD/themes/projektemacher-base/scripts/init/*.sh ; do
    echo "Running $SCRIPT"
    bash "$SCRIPT"
    ERR=$?
    if [ $ERR -ne 0 ] ; then
        echo "Execution of '$SCRIPT' failed!"
        exit $ERR
    fi
done

# Favicons
SOURCE="static/images/kleiderbuegel.png" OPTIONS="-resize 128x128 -fuzz 5% -transparent white" ./themes/projektemacher-base/scripts/favicon.sh

$DEPENDENCY_MANAGER install
#$DEPENDENCY_MANAGER run svgo

./scripts/map.sh
./scripts/svgo.sh
