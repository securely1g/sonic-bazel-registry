# libyang-Python registry entry

`3.1.0-sonic.2` packages upstream libyang-Python 3.1.0 with the four existing
SONiC patches and the shared Bazel binding targets. It uses native-only
`sonic-build-infra 0.0.6-4fb4dca08ea10f7d60e9d217f476fd9a2f975ff2` so AMD64/ARM64
YANG consumers do not depend on the deferred ARMHF registration.

The archive, production patches, CFFI inputs, and binding targets match
`3.1.0-sonic.1`. The new revision records the changed infrastructure dependency;
ordinary module resolution selects it without an override. Native Debian
Trixie AMD64 and ARM64 presubmits run the binding runtime test and all 153
upstream cases.

The prior `3.1.0-sonic.1` was published only in PR snapshots, never registry
`main`. Its original snapshot and all source URLs remain available at
[archive/libyang-python-before-native-split-20260928](https://github.com/securely1g/sonic-bazel-registry/tree/archive/libyang-python-before-native-split-20260928),
commit `edae9085cdf07495d1e790a38ca5b080c526c461`, for existing pinned consumers.
This PR introduces `.2` on the native-only prerequisite branch; it does not
rewrite that historical entry or remove any version from registry `main`.
