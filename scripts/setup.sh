#!/bin/sh

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
SOURCE="static/images/kleiderbuegel.png" OPTIONS="-resize 128x128 -transparent white" ./themes/projektemacher-base/scripts/favicon.sh

yarn install
yarn svgo
