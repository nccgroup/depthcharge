#!/bin/bash

set -e

function run {
    echo $@
    echo -----------------------------------------------
    $@
    echo
}

if [ -z "${DEPTHCHARGE_TEST_ARCH}" ]; then
	export DEPTHCHARGE_TEST_ARCH=arm
fi

run python -m unittest unit

run ./integration/launch_scripts.py
run ./integration/memory_test.py --arch ${DEPTHCHARGE_TEST_ARCH}
run ./integration/memory_test.py
run ./integration/register_test.py

echo 
echo
echo '<-----------------v^v^v^---------||--------o------->'
echo '                                           |        '
echo '       Done! ZOMG SHIPPIT!!!111           ---       '
echo '                                           -        '
echo
