#!/bin/bash

if ! which docker &> /dev/null; then
    echo "Docker is not installed."
    echo "Please install Docker by following the instructions here: https://docs.docker.com/get-docker/"
    exit 1
fi

IMAGE_NAME="stemgen:latest"
REBUILD=0
TRACK_FILE=""

# Parse the arguments
while (( "$#" )); do
  case "$1" in
    -r)
      REBUILD=1
      shift
      ;;
    *)
      if [ -z "$TRACK_FILE" ]; then
        TRACK_FILE=$1
        shift
      else
        echo "Multiple tracks provided or unrecognized argument. Exiting."
        exit 1
      fi
      ;;
  esac
done

if [ -z "$TRACK_FILE" ]; then
    echo "Usage: $0 [-r] /path/to/track.wav"
    echo "-r: Rebuild the Docker image"
    exit 1
fi

# Rebuild Docker image if -r is provided
if [ "$REBUILD" -eq 1 ]; then
    echo "Rebuilding Docker image..."
    docker build -t $IMAGE_NAME "$(dirname "$0")/.."
    echo "Image built successfully."
else
    # Check if Docker image exists
    if ! docker image inspect $IMAGE_NAME &>/dev/null; then
        echo "Docker image not found. Building..."
        docker build -t $IMAGE_NAME "$(dirname "$0")/.."
        echo "Image built successfully."
    fi
fi

TRACK_PATH=$(dirname "$TRACK_FILE")
TRACK_FILENAME=$(basename "$TRACK_FILE")


docker run -v "$(pwd)":/data $IMAGE_NAME "/data/$TRACK_FILENAME" "--output" "/data/output"
