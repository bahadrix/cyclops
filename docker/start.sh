#!/usr/bin/env bash
ABSOLUTE_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
APP_PATH=$(dirname "$(dirname "$ABSOLUTE_PATH")")
DATA_ROOT="${HOME}/.cyclops"
BIND="127.0.0.1:9090"
CONTAINER_NAME="cyclops"
IMAGE_NAME="cyclops"
REDIS_CONTAINER="redis"

while [[ $# -gt 1 ]]
do
key="$1"

case $key in
    -r|--redis-container)
    REDIS_CONTAINER="$2"
    shift
    ;;
    -i|--image-name)
    IMAGE_NAME="$2"
    shift
    ;;
    -n|--name)
    CONTAINER_NAME="$2"
    shift
    ;;
    -b|--bind)
    BIND="$2"
    shift
    ;;
    -d|--data-root)
    DATA_ROOT="$2"
    shift
    ;;
    *)
            # unknown option
    ;;
esac
shift # past argument or value
done

MVP_PATH="${DATA_ROOT}/data"

mkdir -p ${MVP_PATH}

docker run -d --name ${CONTAINER_NAME} -v ${APP_PATH}:/opt/cyclops -v ${MVP_PATH}:/root/.cyclops/data -p ${BIND}:9090 --link ${REDIS_CONTAINER}:redis ${IMAGE_NAME} python /opt/cyclops/cyclops.py -c /opt/cyclops/docker/config.yml
