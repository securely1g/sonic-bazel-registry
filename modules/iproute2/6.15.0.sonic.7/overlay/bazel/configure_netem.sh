#!/bin/sh
# Make runs these execution-platform programs to produce its four netem tables.
set -eu
install -m 755 "$NETEM_MAKETABLE" netem/maketable
install -m 755 "$NETEM_NORMAL" netem/normal
install -m 755 "$NETEM_PARETO" netem/pareto
install -m 755 "$NETEM_PARETONORMAL" netem/paretonormal
exec /bin/sh bazel/configure.sh "$@"
