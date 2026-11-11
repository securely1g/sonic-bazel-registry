#!/usr/bin/env bash
# APT repository evaluation uses file(1) and its magic database to distinguish
# GNU linker scripts from ELF libraries before invoking readelf.
set -euo pipefail

if ! command -v file >/dev/null 2>&1; then
    ROOT=()
    if [[ "$(id -u)" != 0 ]]; then
        ROOT=(sudo -n)
    fi
    "${ROOT[@]}" apt-get -o APT::Update::Error-Mode=any update
    "${ROOT[@]}" apt-get install -y --no-install-recommends file
fi

# Checking the executable alone misses an absent or unusable magic database.
if ! mime_type=$(printf '%s\n' 'INPUT(libncursesw.so.6 -ltinfo)' | file --mime-type -b -); then
    echo "file could not classify a GNU linker script; check its magic database" >&2
    exit 1
fi
if [[ "$mime_type" != text/* ]]; then
    printf 'GNU linker script must have a text MIME type; file reported: %s\n' "$mime_type" >&2
    exit 1
fi
file --version
