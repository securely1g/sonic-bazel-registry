#!/bin/sh
# Preserve the packages' original metadata; relocate only pkgconf's path variables.
set -eu
pcdir="$PWD/.bazel-pkgconfig"
mkdir -p "$pcdir"
for metadata in $BAZEL_PKGCONFIG_FILES; do
    source="$EXT_BUILD_ROOT/$metadata"
    target="$pcdir/$(basename "$metadata")"
    if [ -e "$target" ]; then
        cmp "$source" "$target"
    else
        ln -s "$source" "$target"
    fi
done
export PKG_CONFIG_LIBDIR="$pcdir"
export PKG_CONFIG_PATH=
# Relocation must retain /usr/include's system-header precedence. In particular,
# rdma adds its own newer UAPI directory after inherited CFLAGS.
export PKG_CONFIG_SYSTEM_INCLUDE_PATH="$EXT_BUILD_DEPS/include/usr/include"
CPPFLAGS="$CPPFLAGS -isystem $EXT_BUILD_DEPS/include/usr/include"
export PKG_CONFIG="$BAZEL_PKGCONF --define-variable=prefix=$EXT_BUILD_DEPS --define-variable=libdir=$EXT_BUILD_DEPS/lib --define-variable=includedir=$EXT_BUILD_DEPS/include/usr/include"
# Keep the complete, ordered dependency flags without placing their combined
# expansion in one environment string or recursive Make shell command. GCC's
# standard response files preserve quoting and expand at the same argument
# position. The files remain beside the source throughout configure and Make.
cppflags_file="$PWD/.bazel-cppflags.rsp"
ldflags_file="$PWD/.bazel-ldflags.rsp"
printf '%s\n' "$CPPFLAGS" > "$cppflags_file"
printf '%s\n' "$LDFLAGS" > "$ldflags_file"
# Send dependency preprocessor options directly to cc1: ordinary @ expansion
# would recreate the oversized list in GCC's COLLECT_GCC_OPTIONS environment.
# Driver-only options belong in CFLAGS/LDFLAGS; reject invalid CPPFLAGS early.
if ! $CC $CFLAGS "-Wp,@$cppflags_file" -x c -fsyntax-only /dev/null; then
    echo "iproute2 CPPFLAGS must contain GCC preprocessor options; use CFLAGS/LDFLAGS for driver options" >&2
    exit 1
fi
CPPFLAGS="-Wp,@$cppflags_file"
LDFLAGS="@$ldflags_file"
# Unlike Autoconf, iproute2's probes invoke CC without CFLAGS/CPPFLAGS/LDFLAGS.
# Include the declared toolchain/sysroot flags in those probe commands too.
make_cc="$CC $CFLAGS"
make_cppflags="$CPPFLAGS"
make_cbuildflags="$CPPFLAGS $LDFLAGS"
CC="$CC $CFLAGS $CPPFLAGS $LDFLAGS"
export CC
./configure "$@"
# The upstream Makefiles reset CC and LEX after reading config.mk. GNU Make's
# override assignments keep the selected tools across those recursive builds.
# Keep dependency CPPFLAGS after the source CFLAGS so the bundled newer Linux
# headers take precedence over the distribution headers.
cat >> config.mk <<CONFIG

override CC := $make_cc
override HOSTCC := $make_cc
# The upstream default is /usr/include; select the declared Berkeley DB headers.
override DBM_INCLUDE := $EXT_BUILD_DEPS/include/usr/include
CPPFLAGS := $make_cppflags
LDFLAGS := $LDFLAGS
CBUILD_CFLAGS := $make_cbuildflags
override YACC := $YACC
override LEX := $LEX
export PKG_CONFIG_LIBDIR := $pcdir
export PKG_CONFIG_PATH :=
export PKG_CONFIG_SYSTEM_INCLUDE_PATH := $PKG_CONFIG_SYSTEM_INCLUDE_PATH
CONFIG
