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
    if ! $CC ${CFLAGS:-} "$CPPFLAGS" -x c -fsyntax-only /dev/null; then
        echo "BMv2 CPPFLAGS must contain GCC preprocessor options; use CFLAGS/LDFLAGS for driver options" >&2
        exit 1
    fi
    "$@"
)
