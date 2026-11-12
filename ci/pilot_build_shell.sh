#!/bin/sh
# Use the declared compiler normally. Only libtool's large compiler commands
# can need the bundled kernel to propagate GCC's own posix_spawn errno.
set -eu
if [ "$#" -eq 2 ] && [ "$1" = -c ]; then
    case "$2" in
        bazel-out/*/bin/external/sonic-build-infra+/tools/build_tools/libtool_fixture_foreign_cc/wrapper_build_script.sh)
            : "${SONIC_PILOT_INFRA_WORK:?missing registry work directory}"
            case "$PWD/" in
                "$SONIC_PILOT_INFRA_WORK"/*) ;;
                *) echo "Libtool build ran outside its registry work directory" >&2; exit 1 ;;
            esac
            # pilot_arm.sh already made the enclosing mounts private. The
            # chroot's / is a directory inside a mount, so util-linux cannot
            # apply --make-rprivate to / again.
            exec unshare --mount --propagation unchanged -- "$0" --fixture "$2" "$(readlink /proc/self/ns/mnt)"
            ;;
    esac
fi
if [ "$#" -ne 3 ] || [ "$1" != --fixture ]; then
    exec /bin/bash "$@"
fi
[ "$(readlink /proc/self/ns/mnt)" != "$3" ] || { echo "Expected a private libtool mount namespace" >&2; exit 1; }
fixture="$2"
toolchains='external/sonic-build-infra++gcc+gcc-'
set -- "$PWD"/"$toolchains"*-linux-target-aarch64-host-aarch64/bin
[ "$#" -eq 1 ] && [ -f "$1/aarch64-linux-gnu-gcc" ] && [ -f "$1/aarch64-linux-gnu-g++" ] || {
    echo "Missing or ambiguous ARM64 GCC toolchain for the libtool fixture" >&2; exit 1;
}
toolbin="$1"
SONIC_PILOT_GCC_ORIGINALS=$(mktemp -d "$SONIC_PILOT_INFRA_WORK/.fixture-gcc-XXXXXX")
export SONIC_PILOT_GCC_ORIGINALS
trap 'rm -rf -- "$SONIC_PILOT_GCC_ORIGINALS"' EXIT
for driver in aarch64-linux-gnu-gcc aarch64-linux-gnu-g++; do
    # The generated wrapper finds its declared toolchain relative to $0. Keep
    # the exact script and source it under that original invocation name.
    [ "$(findmnt -n -o PROPAGATION -T "$toolbin/$driver")" = private ] || {
        echo "Expected a private ARM64 GCC mount" >&2; exit 1;
    }
    cp -- "$toolbin/$driver" "$SONIC_PILOT_GCC_ORIGINALS/$driver"
    mount --bind /usr/local/bin/sonic-pilot-compiler "$toolbin/$driver"
done
/bin/bash -c "$fixture"
