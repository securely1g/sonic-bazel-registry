#!/bin/sh
# The SONiC recipe runs boot.sh, configure and Make at the pinned commit.
set -eu
export PATH="$BAZEL_FOREIGN_TOOLS/bin:$PATH"
# Upstream defaults are -g -O2. Retain both when Bazel supplies compiler flags.
export CFLAGS="${CFLAGS:-} -g -O2"
/bin/sh ./boot.sh
exec /bin/sh "$BAZEL_CONFIGURE_ENV" ./configure "$@"
