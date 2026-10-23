# Common metadata generated from Debian recipes

Registers [Common #31](https://github.com/securely1g/sonic-swss-common/pull/31),
source `348987b8f4a3ae97269f59e0817e54f9eed6e19e`. The public
`@sonic-swss-common//:runtime_packages.json` is now generated from existing
`debian/control`, `debian/changelog` and the three runtime TARs. Its label stays
unchanged; the handwritten JSON is removed from the selected source.

The YANG-enabled AMD64 build produces `libswsscommon` version `1.0.0` with
`libyang3 (>= 3.12.2-1)`, where the library's Debian version comes from its own
generated metadata. A no-YANG build omits that dependency. `sonic-db-cli` lists
its actual hiredis and compiler ABI dependencies; it no longer claims to load
`libswsscommon.so` when the binary statically includes that code. These are
observed producer outputs, with no change to runtime compilation or TAR layout.

[Buildimage #30](https://github.com/securely1g/sonic-buildimage/pull/30) consumes
Common's runtime TARs and generated controls in config-engine. Its policy keeps
required installed paths, such as
`usr/lib/x86_64-linux-gnu/libswsscommon.so.0`, rather than package versions or
library dependency lists. [Syncd #13](https://github.com/securely1g/sonic-buildimage/pull/13)
uses the same interface.

This registration consumes the shared generator from
[infra #58](https://github.com/securely1g/sonic-build-infra/pull/58), registered in
[registry #120](https://github.com/securely1g/sonic-bazel-registry/pull/120), and
the compatible library candidates [#131](https://github.com/securely1g/sonic-bazel-registry/pull/131)
and [#132](https://github.com/securely1g/sonic-bazel-registry/pull/132).
[Registry #117](https://github.com/securely1g/sonic-bazel-registry/pull/117)
prepares the declared native runtime used by the existing consumer tests.
All published Common versions remain unchanged; this replaces only the prior
unreleased metadata candidate. Existing C++, Python, Go, Rust, runtime/debug
and timestamp checks remain in the native AMD64/ARM64 registry matrix. CI also
builds and retains the generated metadata; no new DEB producer is introduced.
