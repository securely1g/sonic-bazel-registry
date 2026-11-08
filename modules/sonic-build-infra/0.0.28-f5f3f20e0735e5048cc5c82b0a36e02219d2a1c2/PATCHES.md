# Registry patches for build-infra .28

The raw source is [sonic-build-infra f5f3f20e](https://github.com/securely1g/sonic-build-infra/commit/f5f3f20e0735e5048cc5c82b0a36e02219d2a1c2).
Apply the complete patch set below in order with strip level 1, then the four
registry overlays declared in `source.json`. The source archive's 439 files were
checked byte-for-byte and mode-for-mode against that Git tree; its SHA-256 is
`01905bbe18b91f319db83629cc0f90b8a6e297fd1e9cffb28cae320ebcf3f854`.

## 0001-bump-version.patch

Purpose: align the distributed `MODULE.bazel` identity from `0.0.28` to this
registry version, `0.0.28-f5f3f20e0735e5048cc5c82b0a36e02219d2a1c2`, without
changing dependencies or build behavior.

Origin/reference: retain the version-alignment patch from the existing
[PR287 candidate at 4b427f63](https://github.com/securely1g/sonic-bazel-registry/blob/4b427f63cc7493b20af9a95c0c77ca0d365e7f12/modules/sonic-build-infra/0.0.28-b55ad3322094b87a682b6ef22ec500696a183b6d/patches/0001-bump-version.patch),
changing only its replacement version to identify the new source commit.

Upstream status: this is registry-specific version alignment. The pinned raw
source declares `0.0.28`; the commit-qualified registry identity is supplied by
this patch. No upstream feature fix or upstream merge is claimed.

Validation: the retained ordered-patch check applied this exact patch to the
verified f5 Git preimage and compared the result with the registered MODULE.
The patch integrity in `source.json` matches its bytes. No native validation was
run as part of this registration refresh.

## 0002-registry-cross-test-visibility.patch

Purpose: permit external registry validation to refer to the existing
`kernel_cross_runtime_<architecture>_test` executables and `kernel_runtime_test`
by adding public target visibility. It does not change their code, arguments or
platform restrictions.

Origin/reference: preserve the existing
[PR287 visibility patch at 4b427f63](https://github.com/securely1g/sonic-bazel-registry/blob/4b427f63cc7493b20af9a95c0c77ca0d365e7f12/modules/sonic-build-infra/0.0.28-b55ad3322094b87a682b6ef22ec500696a183b6d/patches/0002-registry-cross-test-visibility.patch)
byte-for-byte. Its preimage is
[the pinned source's build-tool declarations](https://github.com/securely1g/sonic-build-infra/blob/f5f3f20e0735e5048cc5c82b0a36e02219d2a1c2/tools/build_tools/BUILD.bazel).

Upstream status: those two public-visibility additions are absent from the
pinned f5 source and remain an external registry patch. No upstream submission
or merge evidence is recorded here.

Validation: the retained ordered-patch check applied this unchanged patch after
0001 to the verified source preimage and checked the declared overlay
integrities. Existing AMD64 registry cross-tool checks remain selected. The
presubmit retains 42 builds and 44 existing tests and adds only the public-owner
alias regression, for 45 tests; current native execution is pending. Exposing
`kernel_runtime_test` does not select it: the current presubmit retains the
`kernel_runtime_tools_test` tools-only check and excludes the package-producing
runtime test. This documentation does not authorize broader owner CI.
