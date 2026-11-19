#!/usr/bin/env bash
set -euo pipefail

export LD_LIBRARY_PATH="$(dirname "$3"):$(dirname "$4"):$(dirname "$5")"
export LD_BIND_NOW=1
for executable in "$1" "$2"; do
    dynamic=$(readelf -d "$executable")
    [[ "$dynamic" == *'[libapt_runtime_parent.so.1]'* ]]
    [[ "$dynamic" != *'[libapt_runtime_leaf.so.1]'* ]]
    [[ "$dynamic" != *'[libapt_runtime_other.so.1]'* ]]
    [[ "$dynamic" != *'(RUNPATH)'* && "$dynamic" != *'(RPATH)'* ]]
    "$executable"
done
