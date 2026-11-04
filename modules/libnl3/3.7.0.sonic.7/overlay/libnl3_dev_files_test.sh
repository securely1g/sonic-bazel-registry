#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
core=$(realpath "$1")
route=$(realpath "$2")
runtime_core=$(realpath "$3")
runtime_route=$(realpath "$4")
runtime_genl=$(realpath "$5")
runtime_nf=$(realpath "$6")
runtime_cli=$(realpath "$7")
multiarch=$(cc -print-multiarch)
case "$multiarch" in
    x86_64-linux-gnu|aarch64-linux-gnu) ;;
    *) echo "Unsupported native architecture: $multiarch" >&2; exit 1 ;;
esac

# These are the two Debian 3.7.0-0.2 development-package file splits, with
# /lib canonicalized to /usr/lib for SONiC's merged-/usr filesystem.
python3 - "$core" "$route" "$multiarch" "$runtime_core" "$runtime_route" "$runtime_genl" "$runtime_nf" "$runtime_cli" <<'CHECK'
import pathlib, sys, tarfile

core, route, triplet = sys.argv[1:4]
inventories = []
for archive, stem in ((core, 'libnl-3'), (route, 'libnl-route-3')):
    with tarfile.open(archive) as source:
        files = {member.name.removeprefix('./'): member for member in source if not member.isdir()}
    prefix = f'usr/lib/{triplet}/'
    expected = {prefix + stem + '.a', prefix + stem + '.so', prefix + 'pkgconfig/' + stem + '.0.pc'}
    headers = {path for path in files if path.startswith('usr/include/libnl3/netlink/') and path.endswith('.h')}
    if stem == 'libnl-3':
        assert len(headers) > 100, headers
        assert 'usr/include/libnl3/netlink/version.h' in headers
        assert 'usr/include/libnl3/netlink/route/route.h' in headers
    else:
        assert not headers
    assert set(files) == expected | headers, set(files) ^ (expected | headers)
    for path, member in files.items():
        assert member.uid == member.gid == 0, (path, member.uid, member.gid)
        if path.endswith('.so'):
            assert member.issym() and member.linkname == stem + '.so.200', path
        else:
            assert member.isfile() and member.mode == 0o644, (path, member.mode)
    inventories.append(set(files))
assert not inventories[0] & inventories[1], inventories[0] & inventories[1]
for archive, stem in zip(sys.argv[4:], ('libnl-3', 'libnl-route-3', 'libnl-genl-3', 'libnl-nf-3', 'libnl-cli-3')):
    with tarfile.open(archive) as source:
        files = {m.name.removeprefix('./'): m for m in source if not m.isdir()}
    prefix = f'usr/lib/{triplet}/'
    expected = {prefix + stem + '.so.200', prefix + stem + '.so.200.26.0'}
    if stem == 'libnl-3':
        expected |= {'etc/libnl-3/classid', 'etc/libnl-3/pktloc'}
    if stem == 'libnl-cli-3':
        expected |= {prefix + 'libnl-3/cli/' + p + '.so' for p in (
            'cls/basic', 'cls/cgroup', 'qdisc/bfifo', 'qdisc/blackhole', 'qdisc/fq_codel',
            'qdisc/hfsc', 'qdisc/htb', 'qdisc/ingress', 'qdisc/pfifo', 'qdisc/plug')}
    assert set(files) == expected, (stem, set(files) ^ expected)
    assert not (set(files) & set.union(*inventories))
    for path, member in files.items():
        assert member.uid == member.gid == 0, path
        if member.issym():
            assert member.linkname == stem + '.so.200.26.0', path
        else:
            assert member.isfile() and member.mode == 0o644, (path, member.mode)
CHECK

root="$TEST_TMPDIR/installed"
mkdir -p "$root"
for archive in "$runtime_core" "$runtime_route" "$core" "$route"; do
    tar -xf "$archive" -C "$root"
done
libdir="$root/usr/lib/$multiarch"
export NLSYSCONFDIR="$root/etc/libnl-3"
strings "$libdir/libnl-route-3.so.200" | grep -Fx /etc/libnl-3 > /dev/null
cat > "$TEST_TMPDIR/consumer.c" <<'C'
#include <netlink/netlink.h>
#include <netlink/socket.h>
#include <netlink/route/link.h>
#include <netlink/route/pktloc.h>
int main(void) {
    struct nl_sock *socket = nl_socket_alloc();
    struct rtnl_link *link = rtnl_link_alloc();
    struct rtnl_pktloc *location = 0;
    if (!socket || !link || rtnl_pktloc_lookup("ip.src", &location) < 0) return 1;
    rtnl_pktloc_put(location);
    rtnl_link_put(link);
    nl_socket_free(socket);
    return 0;
}
C
cc -Wall -Werror -I"$root/usr/include/libnl3" "$TEST_TMPDIR/consumer.c" \
    -L"$libdir" -Wl,-rpath-link,"$libdir" -lnl-route-3 -lnl-3 -o "$TEST_TMPDIR/shared"
LD_PRELOAD="$libdir/libnl-3.so.200:$libdir/libnl-route-3.so.200" \
    LD_LIBRARY_PATH="$libdir" "$TEST_TMPDIR/shared"

# Force every archive member into the link: this detects missing generated
# parser objects and accidental duplication of core objects in the route archive.
cc -Wall -Werror -I"$root/usr/include/libnl3" "$TEST_TMPDIR/consumer.c" \
    -Wl,--whole-archive "$libdir/libnl-route-3.a" "$libdir/libnl-3.a" \
    -Wl,--no-whole-archive -lm -pthread -ldl -o "$TEST_TMPDIR/static"
if readelf -d "$TEST_TMPDIR/static" | grep -q 'NEEDED.*libnl'; then
    echo 'Static consumer unexpectedly loads a libnl DSO' >&2
    exit 1
fi
"$TEST_TMPDIR/static"
