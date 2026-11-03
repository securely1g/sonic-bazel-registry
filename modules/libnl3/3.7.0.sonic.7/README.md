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
