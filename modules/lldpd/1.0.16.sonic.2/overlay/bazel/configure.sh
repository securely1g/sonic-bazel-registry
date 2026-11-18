#!/bin/sh
# Preserve Debian's feature selection and SONiC's two netlink buffer settings.
set -eu
export PATH="$BAZEL_FOREIGN_TOOLS/bin:$PATH"
export PKG_CONFIG_LIBDIR="$LLDPD_TARGET_ROOT/usr/lib/x86_64-linux-gnu/pkgconfig:$LLDPD_TARGET_ROOT/usr/share/pkgconfig"
export PKG_CONFIG_SYSROOT_DIR="$LLDPD_TARGET_ROOT"
export CPPFLAGS="${CPPFLAGS:-} -idirafter $LLDPD_TARGET_ROOT/usr/include -idirafter $LLDPD_TARGET_ROOT/usr/include/x86_64-linux-gnu"
export CFLAGS="${CFLAGS:-} -O2 -g -fstack-protector-strong -Wformat -Werror=format-security -D_FORTIFY_SOURCE=2"
export LDFLAGS="${LDFLAGS:-} -L$LLDPD_TARGET_ROOT/usr/lib/x86_64-linux-gnu -Wl,-rpath-link,$LLDPD_TARGET_ROOT/usr/lib/x86_64-linux-gnu -Wl,-z,relro,-z,now -Wl,--build-id=sha1"
# net-snmp-config is shell metadata from the selected TARGET development
# package. Relocate only its installed include/library paths into that root.
cat > "$PWD/bazel-net-snmp-config" <<'SNMP'
#!/bin/sh
set -eu
/bin/sh "$LLDPD_TARGET_ROOT/usr/bin/net-snmp-config" "$@" |
    sed -e "s|-I/usr/|-idirafter $LLDPD_TARGET_ROOT/usr/|g" \
        -e "s|-L/usr/|-L$LLDPD_TARGET_ROOT/usr/|g" \
        -e "s| /usr/lib/| $LLDPD_TARGET_ROOT/usr/lib/|g"
SNMP
chmod +x "$PWD/bazel-net-snmp-config"
export NETSNMP_CONFIG="$PWD/bazel-net-snmp-config"
# Debian's completion patch edits Makefile.am; regenerate its installed input.
autoreconf -fi
exec /bin/sh "$BAZEL_CONFIGURE_ENV" ./configure "$@"
