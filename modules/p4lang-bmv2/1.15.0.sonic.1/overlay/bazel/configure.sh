#!/bin/sh
# Run the maintained Autotools build with declared tools and target metadata.
set -eu
export PATH="$BAZEL_P4_TOOLS/bin:$PATH"
export PYTHON="$BAZEL_P4_TOOLS/bin/python3"
export THRIFT="$BAZEL_P4_TOOLS/bin/thrift"
export PROTOC="$BAZEL_P4_TOOLS/bin/protoc"
export GRPC_CPP_PLUGIN="$BAZEL_P4_TOOLS/bin/grpc_cpp_plugin"
export GRPC_PY_PLUGIN="$BAZEL_P4_TOOLS/bin/grpc_python_plugin"

pcdir="$PWD/.bazel-pkgconfig"
mkdir -p "$pcdir"
for metadata in $BAZEL_PKGCONFIG_FILES; do
    source="$EXT_BUILD_ROOT/$metadata"
    target="$pcdir/$(basename "$metadata")"
    if [ -e "$target" ]; then cmp "$source" "$target"; else ln -s "$source" "$target"; fi
done
export PKG_CONFIG_LIBDIR="$pcdir"
export PKG_CONFIG_PATH=
export PKG_CONFIG_SYSTEM_INCLUDE_PATH="$EXT_BUILD_DEPS/include/usr/include"
export PKG_CONFIG="$BAZEL_PKGCONF --define-variable=prefix=$EXT_BUILD_DEPS --define-variable=libdir=$EXT_BUILD_DEPS/lib --define-variable=includedir=$EXT_BUILD_DEPS/include/usr/include"
CPPFLAGS="${CPPFLAGS:-} -isystem $EXT_BUILD_DEPS/include/usr/include"
export CPPFLAGS

# autoreconf follows AC_CONFIG_SUBDIRS to prepare simple_switch_grpc as well.
"$BAZEL_P4_TOOLS/bin/autoreconf" -fi
exec ./configure "$@"
