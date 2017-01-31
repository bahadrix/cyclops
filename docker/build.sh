#!/usr/bin/env bash

IMAGE_NAME="cyclops"

while [[ $# -gt 1 ]]
do
key="$1"

case $key in
    -n|--name)
    IMAGE_NAME="$2"
    shift
    ;;
    *)
            # unknown option
    ;;
esac
shift
done

docker build -t ${IMAGE_NAME} .