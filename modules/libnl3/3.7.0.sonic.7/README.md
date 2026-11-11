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
published `.6` entry is untouched. This version retains `.6`'s existing overlays,
applies the native-build patch proposed in closed registry PR #148 unchanged,
then applies two small patches for the output names and SDK timestamps.

The new raw consumer calls main, generic-netlink, route, netfilter and CLI APIs
through the actual shared targets. It uses ordinary Bazel runfiles, compares
`dladdr` results with each declared provider artifact and checks each SONAME
filename. It does not unpack a runtime TAR, set `LD_LIBRARY_PATH` or select a
custom loader. Existing installed-consumer, SDK/path and TAR tests remain in
both AMD64 and ARM64 jobs. The independent consumer module has no source or
version overrides.

The minimum infrastructure is the published
`0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88` registration (build-infra
#67), which provides the native execution helpers, runtime-package metadata and
debug-file contract used here. Public Distroless `.14`, `tar.bzl`
`0.10.5.sonic.1` and rules_cc `0.2.22` keep this ordinary dependent root
compatible without root-only workarounds. The module, fetched overlay and test
consumer declare the same minimum. No DEB target is added or run.

The header and exact development-library TARs use the existing `tar.bzl`
`default_mtime` attribute with epoch `1672560000`. This prevents patched headers,
generated pkg-config files and static libraries from inheriting build-time
filesystem timestamps; explicit library-link timestamps remain zero. The
existing package test checks both exact SDK splits and aggregate header times.
The existing pkg-config TAR also declares root ownership through upstream
`mutate(owner="0", group="0")`, so synthesized parent directories do not
inherit the builder UID/GID. The package test checks every aggregate member,
including directories. Payload bytes, modes and symlink targets are unchanged.
