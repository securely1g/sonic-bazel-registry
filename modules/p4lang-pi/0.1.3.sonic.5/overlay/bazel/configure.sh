#!/bin/sh
set -eu
export PATH="$BAZEL_FOREIGN_TOOLS/bin:$PATH"
export PYTHON="$BAZEL_FOREIGN_TOOLS/bin/python3"
export PROTOC="$BAZEL_FOREIGN_TOOLS/bin/protoc"
export GRPC_CPP_PLUGIN="$BAZEL_FOREIGN_TOOLS/bin/grpc_cpp_plugin"
export GRPC_PY_PLUGIN="$BAZEL_FOREIGN_TOOLS/bin/grpc_python_plugin"
pcdir="$PWD/.bazel-pkgconfig"
mkdir -p "$pcdir"
for metadata in $BAZEL_PKGCONFIG_FILES; do
    source="$EXT_BUILD_ROOT/$metadata"
    target="$pcdir/$(basename "$metadata")"
    if [ -e "$target" ]; then cmp "$source" "$target"; else ln -s "$source" "$target"; fi
done
export PKG_CONFIG_LIBDIR="$pcdir"
export PKG_CONFIG_PATH=
export PKG_CONFIG="$BAZEL_FOREIGN_TOOLS/bin/pkgconf --define-variable=prefix=$EXT_BUILD_DEPS --define-variable=libdir=$EXT_BUILD_DEPS/lib --define-variable=includedir=$EXT_BUILD_DEPS/include/usr/include"
"$BAZEL_FOREIGN_TOOLS/bin/autoreconf" -fi
exec /bin/sh "$BAZEL_CONFIGURE_ENV" ./configure "$@" --with-boost="$EXT_BUILD_DEPS/include/usr" --with-boost-libdir="$EXT_BUILD_DEPS/lib"
