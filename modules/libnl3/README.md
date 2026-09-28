## SWSS dependency releases

### libnl3 3.7.0-sonic.2

The version follows the [registry policy](https://github.com/securely1g/sonic-bazel-registry/blob/main/README.md#module-version-convention): `3.7.0` is the upstream libnl
version and `2` is the SONiC revision. The already-published
`3.7.0.sonic-buildimage` baseline counts as revision 1 and keeps its original
name and contents for existing consumers. This header-isolation update is
revision 2; no separate `3.7.0-sonic.1` entry is introduced.

This release uses the same libnl 3.7.0 archive and SONiC RTA_NH_ID patch as
`3.7.0.sonic-buildimage`. The change is in `overlay/libnl3.BUILD`:
`linux_private_headers` no longer uses `strip_include_prefix`. That attribute
exported libnl's private Linux headers as transitive virtual include paths, so
SWSS consumers could pick those headers instead of the toolchain's kernel UAPI
headers. libnl itself still selects its private headers through the local
`LIBNL_COPTS` and Bison include flags.

The overlay is repeated because each registry version must be independently
fetchable; it is not a second libnl source fork. The unchanged RTA_NH_ID patch is
part of that complete overlay, not the reason for the new version.

The release's `presubmit.json` validates native AMD64 on Debian Trixie with Bazel
8.5.1. Its consumer selects the published `sonic-build-infra` 0.0.4 platform.
It builds all five runtime and five development archives, then runs a public
Bazel consumer and an extracted-package test. The consumer round-trips a
route carrying the SONiC RTA_NH_ID attribute and requires a kernel UAPI attribute
that is absent from libnl's private headers. The package test checks SONAMEs,
relative library symlinks, public header and pkg-config paths, an installed
consumer, and immediate loading of every shipped library and CLI plugin.

The archive is now fetched from Debian's HTTPS mirror with the same SHA256 as the
previous URL. ARM64 is not declared because the current archive and pkg-config
paths are fixed to `x86_64-linux-gnu`. This release does not provide detached debug
packages; downstream SONiC image behavior remains a separate validation boundary.

Consumers adopting this release must update their dependency version and pinned
registry snapshot together, then check the resolved graph according to the
[registry migration guidance](https://github.com/securely1g/sonic-bazel-registry/blob/main/README.md#check-bazels-selected-version).
