#!/usr/bin/env bash
#DOCKER_IMAGE="yeslogic/prince:latest"

set -e

if [ -z "$1" ] ; then
    hugo -F -D --renderSegments print
    npx vivliostyle build --language de docs/print.html -o print.pdf
    gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.5 -dPDFSETTINGS=/ebook -dFastWebView -dUseCropBox -dNOPAUSE -dBATCH -sOutputFile=docs/catalogue.pdf print.pdf
else
    hugo -F -D --environment print --renderSegments print
    npx vivliostyle build --preflight press-ready --language de docs/print.html -o print.pdf
    # docker pull "$DOCKER_IMAGE"
    # if [ $? -ne 0 ]; then
    #     echo
    #     echo "Failed to get Docker image ($IMAGE), is the deamon running?"
    #     exit 1
    # fi

    # docker run -v `pwd`:`pwd` -w `pwd` $DOCKER_IMAGE --fileroot `pwd`/docs docs/print.html -o catalogue.pdf
fi

