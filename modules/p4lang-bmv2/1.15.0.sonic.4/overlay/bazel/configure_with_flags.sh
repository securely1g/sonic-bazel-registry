# Sourced by rules_foreign_cc's public configure_prefix before /bin/sh exec.
# Preserve the full ordered preprocessing list before it exceeds Linux's
# per-environment-string bound. Forward the response directly to cc1, avoiding
# GCC's expansion into another oversized COLLECT_GCC_OPTIONS environment entry.
(
    set -eu
    cppflags_file="$PWD/.bazel-bmv2-cppflags.rsp"
    printf '%s\n' "${CPPFLAGS:-}" > "$cppflags_file"
    # This is the same final native include added by the original configure
    # adapter. Keep it after every original flag, including existing -isystem
    # paths; moving it ahead of the response would change header precedence.
    native_include="$EXT_BUILD_DEPS/include/usr/include"
    case "$native_include" in
        *'"'*|*'\'*) echo "Unsupported quote or backslash in native include path" >&2; exit 1 ;;
    esac
    printf '%s\n' "-isystem" "\"$native_include\"" >> "$cppflags_file"
    export CPPFLAGS="-Wp,@$cppflags_file"
    # Compact linker flags before the first exec as well. GCC's normal @file
    # expansion can overflow COLLECT_GCC_OPTIONS; the existing shared compiler
    # launcher recognizes this private argument vector and shortens its -L
    # paths for each actual working directory before invoking GCC.
    ldflags_file="$PWD/.sonic-linker-arguments"
    printf '%s\n' "${LDFLAGS:-}" > "$ldflags_file.raw"
    export LDFLAGS="@$ldflags_file"
    "$BAZEL_P4_TOOLS/bin/python3" - "$ldflags_file.raw" "$ldflags_file" <<'PY'
import pathlib
import shlex
import sys

arguments = shlex.split(pathlib.Path(sys.argv[1]).read_text())
if any("\n" in value or "\r" in value for value in arguments):
    raise ValueError("BMv2 linker arguments cannot contain line breaks")
pathlib.Path(sys.argv[2]).write_text(
    "sonic-linker-arguments-v1\n" + "".join(value + "\n" for value in arguments)
)
PY
    if ! $CC ${CFLAGS:-} "$CPPFLAGS" -x c -fsyntax-only /dev/null; then
        echo "BMv2 CPPFLAGS must contain GCC preprocessor options; use CFLAGS/LDFLAGS for driver options" >&2
        exit 1
    fi
    "$@"
)
