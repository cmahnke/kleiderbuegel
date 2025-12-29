#!/usr/bin/env bash
#DOCKER_IMAGE="yeslogic/prince:latest"

set -e

REQUIRED_GS_VERSION="10.06.0"
CURRENT_GS_VERSION=$(gs --version)



if [ -z "$1" ] ; then
    hugo -F -D --renderSegments print
    npx vivliostyle build --language de docs/print.html -o print.pdf
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/ebook -dFastWebView -dUseCropBox -dNOPAUSE -dBATCH -sOutputFile=docs/catalogue.pdf print.pdf
else
    if [ "$(printf '%s\n' "$REQUIRED_GS_VERSION" "$CURRENT_GS_VERSION" | sort -V | head -n1)" != "$REQUIRED_GS_VERSION" ]; then
        echo "Error: Ghostscript version $REQUIRED_GS_VERSION or higher is required. Found $CURRENT_GS_VERSION."
        exit 1
    fi

    ICC_PROFILE=ISOcoated_v2_eci.icc
    ICC_PROFILE_DIR=""
    if [ -d "/usr/share/color/icc" ] ; then
        ICC_PROFILE_DIR="/usr/share/color/icc"
    elif [ -d "/usr/local/share/color/icc" ] ; then
        ICC_PROFILE_DIR="/usr/local/share/color/icc"
    elif [ -d "/Library/ColorSync/Profiles" ] ; then
        ICC_PROFILE_DIR="/Library/ColorSync/Profiles"
    fi

    if [ ! -f "$ICC_PROFILE_DIR$ICC_PROFILE" ] ; then
      wget -nc https://github.com/GitBruno/myProfiles/raw/refs/heads/master/ECI_Offset_2009/ISOcoated_v2_eci.icc
      ICC_PROFILE_DIR="."
      echo "Downloaded ICC profile"
    else 
      echo "Using ICC Profiles from $ICC_PROFILE_DIR"
    fi

    hugo -F -D --environment print --renderSegments print
    npx vivliostyle build --preflight press-ready --preflight-option boundary-boxes --language de docs/print.html -o print-press-ready.pdf

    # See https://ghostscript.readthedocs.io/en/latest/VectorDevices.html
    # gs -dPDFX=4 -dBATCH -dNOPAUSE -dSAFER -sDEVICE=pdfwrite \
    ##  -units PixelsPerInch -density 600 \
    #   -dPDFSETTINGS=/print -r600 -dGrayImageResolution=600 -dMonoImageResolution=600 -dColorImageResolution=600 \
    #   -dCompatibilityLevel=1.6 -dPDFSETTINGS=/printer \
    #   -dDEVICEWIDTHPOINTS=612.28 -dDEVICEHEIGHTPOINTS=612.28 -dFIXEDMEDIA \
    #   -sProcessColorModel=DeviceCMYK -sColorConversionStrategy=UseDeviceIndependentColor -sDefaultRGBProfile=sRGB.icc \
    #   -sOutputFile=print-press-ready_X4.pdf \
    #   -c '<</PageOffset [8.5 8.5]>> setpagedevice' \
    #   -c '<< /TrimBox [8.5 8.5 603.78 603.78] /BleedBox [0 0 612.28 612.28] >> setpagedevice' \
    #   -f print-press-ready.pdf


    #-sICCProfilesDir=$ICC_PROFILE_DIR -sOutputICCProfile=ISOcoated_v2_eci.icc \
    # -sICCProfilesDir=$ICC_PROFILE_DIR -sOutputICCProfile=ISOcoated_v2_eci.icc


fi
