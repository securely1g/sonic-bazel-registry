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

Consumers adopting this release must update their dependency version and pinned
registry snapshot together, then check the resolved graph according to the
[registry migration guidance](https://github.com/securely1g/sonic-bazel-registry/blob/main/README.md#check-bazels-selected-version).
