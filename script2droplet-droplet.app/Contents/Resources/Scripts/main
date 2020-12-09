#!/usr/bin/env bash

## No bash script should be considered releasable until it has this! http://j.mp/safebash ##
# Exit if any statement returns a non-true return value (non-zero).
set -o errexit
# Exit on use of an uninitialized variable
set -o nounset

cd $(dirname $0)/../../..
for script in "${@}"; do
    base="$(basename $script .sh)"
    cp -r $PWD ../${base}-droplet.app
    cp $script ../${base}-droplet.app/Contents/Resources/Scripts/main
done
