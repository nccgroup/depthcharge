#!/bin/sh
#
# Update script help text entries
#
################################################################################

THIS_DIR=$(realpath $(dirname $0))
SCRIPT_DIR=$(realpath ${THIS_DIR}/../python/scripts)
DOC_DIR=${THIS_DIR}/src/scripts

echo "Writing help text output to ${DOC_DIR}"

set -e
for name in $(ls "${SCRIPT_DIR}" | grep 'depthcharge-'); do
	script=${SCRIPT_DIR}/${name}
	echo "	$name --help > ${DOC_DIR}/${name}.txt"
	$script --help > ${DOC_DIR}/${name}.txt
done


