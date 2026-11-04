# Native libnl3 shared-library filenames

Common's normal C++ and Rust tests link the native libnl shared providers through
`dynamic_deps`. Those libraries advertise ABI SONAMEs such as `libnl-3.so.200`,
but the previous build left the generated filename as `liblibnl_3_shared.so`.
Bazel propagated the right runfiles directory, yet the loader could not find the
name in `DT_NEEDED`. Tests that unpacked the installed runtime TAR already had
the correct SONAME symlink and did not expose this failure.

Version `3.7.0.sonic.7` gives all five shared provider outputs their existing
SONAME filenames. The ABI versions, public labels, source archive, SONiC fixes,
installed TAR paths, SDK contracts and debug pairing remain unchanged. The
published `.6` entry and its exact-tree exception are untouched. This version
retains `.6`'s existing overlays and native-build patch from registry PR #148,
then applies one small additional patch for the output names and regression.

The new raw consumer calls main, generic-netlink, route, netfilter and CLI APIs
through the actual shared targets. It uses ordinary Bazel runfiles, compares
`dladdr` results with each declared provider artifact and checks each SONAME
filename. It does not unpack a runtime TAR, set `LD_LIBRARY_PATH` or select a
custom loader. Existing installed-consumer, SDK/path and TAR tests remain in
both AMD64 and ARM64 jobs. The independent consumer module has no source or
version overrides.

The minimum infrastructure is the reviewed `0.0.26-0378d538...` registration,
with the existing native execution helpers and 0644 debug-file contract. Public
Distroless `.14`, `tar.bzl` `0.10.5.sonic.1` and rules_cc `0.2.22` keep this
ordinary dependent root compatible without root-only workarounds. No DEB target
is added or run.

Validation is pending while the focused source and regression graph is prepared.

The ordinary consumer now selects the accepted cumulative build-infra candidate
`0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568` from registry PR #195.
This replaces the retired draft declaration without changing libnl source,
compiler options, installed libraries, or its existing SDK/debug regressions.

The ordinary consumer now selects the sole current infrastructure candidate from [registry #209](https://github.com/securely1g/sonic-bazel-registry/pull/209). The module, fetched overlay and test consumer declare the same minimum. Source features, SDK outputs and all four tests remain unchanged; fresh acceptance is pending.

The header and exact development-library TARs use the existing `tar.bzl`
`default_mtime` attribute with epoch `1672560000`. This prevents patched headers,
generated pkg-config files and static libraries from inheriting build-time
filesystem timestamps; explicit library-link timestamps remain zero. The
existing package test checks both exact SDK splits and aggregate header times.
The existing pkg-config TAR also declares root ownership through upstream
`mutate(owner="0", group="0")`, so synthesized parent directories do not
inherit the builder UID/GID. The package test checks every aggregate member,
including directories. Payload bytes, modes and symlink targets are unchanged.
