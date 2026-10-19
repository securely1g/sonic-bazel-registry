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
CPPFLAGS := $make_cppflags
LDFLAGS := $LDFLAGS
CBUILD_CFLAGS := $make_cbuildflags
override YACC := $YACC
override LEX := $LEX
export PKG_CONFIG_LIBDIR := $pcdir
export PKG_CONFIG_PATH :=
export PKG_CONFIG_SYSTEM_INCLUDE_PATH := $PKG_CONFIG_SYSTEM_INCLUDE_PATH
CONFIG
