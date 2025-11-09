#!/usr/bin/env bash
DOCKER_IMAGE="yeslogic/prince:latest"


docker pull "$DOCKER_IMAGE"
if [ $? -ne 0 ]; then
  echo
  echo "Failed to get Docker image ($IMAGE), is the deamon running?"
  exit 1
fi

hugo -F -D 

docker run -v `pwd`:`pwd` -w `pwd` $DOCKER_IMAGE --fileroot `pwd`/docs docs/print.html -o catalogue.pdf
