#!/usr/bin/env bash

set -e

echo "The eBook output ic currently not optimized! Exiting"
exit 1
hugo -F -D --renderSegments ebook
npx vivliostyle build  --language de docs/print.html -o print.epub