# Registry patches for build-infra .28

The raw source is [sonic-build-infra 58112470](https://github.com/securely1g/sonic-build-infra/commit/58112470001b1c450fd9e859079e92c62c236242).
Apply the complete patch set below in order with strip level 1, then the four
registry overlays declared in `source.json`. The source archive's 444 files were
checked byte-for-byte and mode-for-mode against that Git tree; its SHA-256 is
`2aeab409c1d2bb2bc16197520047385d424ea402b24118f755f67bfe7746e8a0`.

## 0001-bump-version.patch

Purpose: align the distributed `MODULE.bazel` identity from `0.0.28` to this
registry version, `0.0.28-58112470001b1c450fd9e859079e92c62c236242`, without
changing dependencies or build behavior.

Origin/reference: retain the version-alignment patch from the existing
[PR287 candidate at 4b427f63](https://github.com/securely1g/sonic-bazel-registry/blob/4b427f63cc7493b20af9a95c0c77ca0d365e7f12/modules/sonic-build-infra/0.0.28-b55ad3322094b87a682b6ef22ec500696a183b6d/patches/0001-bump-version.patch),
changing only its replacement version to identify the new source commit.

Upstream status: this is registry-specific version alignment. The pinned raw
source declares `0.0.28`; the commit-qualified registry identity is supplied by
this patch. No upstream feature fix or upstream merge is claimed.

Validation: the retained ordered-patch check applied this exact patch to the
verified 58112470 Git preimage and compared the result with the registered MODULE.
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
[the pinned source's build-tool declarations](https://github.com/securely1g/sonic-build-infra/blob/58112470001b1c450fd9e859079e92c62c236242/tools/build_tools/BUILD.bazel).

Upstream status: those two public-visibility additions are absent from the
pinned 58112470 source and remain an external registry patch. No upstream submission
or merge evidence is recorded here.

Validation: the retained ordered-patch check applied this unchanged patch after
0001 to the verified source preimage and checked the declared overlay
integrities. Existing AMD64 registry cross-tool checks remain selected. The
presubmit retains 42 builds and all 45 existing tests, including the public-owner
alias regression, and adds the two paired native regressions, for 47 tests;
current registry execution is pending. Exposing
`kernel_runtime_test` does not select it: the current presubmit retains the
`kernel_runtime_tools_test` tools-only check and excludes the package-producing
runtime test. This documentation does not authorize broader owner CI.
