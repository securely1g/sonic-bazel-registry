#!/usr/bin/env bash
# Transport Linux validation evidence without artifact-service filename changes.
set -euo pipefail

artifacts=$(realpath -m -- "$1")
archive=$(realpath -m -- "$2")
case "$archive" in
  "$artifacts"|"$artifacts"/*)
    echo "The evidence archive must be outside the input directory" >&2
    exit 1
    ;;
esac
if [[ ! -d "$artifacts" ]]; then
  echo "No validation evidence directory was created"
  exit 0
fi

temporary=$(mktemp "${archive}.XXXXXX")
trap 'rm -f -- "$temporary"' EXIT
tar --create --file="$temporary" --directory="$artifacts" .
mv -- "$temporary" "$archive"
