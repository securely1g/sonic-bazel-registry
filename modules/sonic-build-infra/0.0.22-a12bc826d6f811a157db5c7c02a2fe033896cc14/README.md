# Generated Debian metadata with cache-safe kernel tools

Registers `0.0.22-a12bc826d6f811a157db5c7c02a2fe033896cc14` from the merged
[build-infra source](https://github.com/securely1g/sonic-build-infra/tree/a12bc826d6f811a157db5c7c02a2fe033896cc14).
The source retains the static build-tool launcher and generated Debian metadata
support, including complete control fields and runtime TAR hashes.

For example, Common's `libswsscommon` version `1.0.0` and
`//dist:libswsscommon_pkg` supply config-engine's installed package record.
Package identity and dependency fields come from the owner's Debian
control/changelog; target ELF files determine shared-library requirements.
The receipt preserves fields such as `Description`, `Maintainer` and `Source`
while requiring every field to match the reviewed package contract.
No new Debian packages are produced.

## Cached kernel tools

This source includes [build-infra #64](https://github.com/securely1g/sonic-build-infra/pull/64).
Consumers must select the targeted download policy in their root configuration,
because dependency `.bazelrc` files are not inherited:

```text
build --remote_download_regex=(^|.*/)tools/build_tools/kernel_runtime_(amd64|arm64)(/.*)?$
```

The shared registry runner passes the flag explicitly because it ignores rc files.
The kernel tool tree keeps its directory symlinks. Canonical `/usr/lib` package
lookup and protection of raw ELF executables behind launcher aliases remain.

| Input or action | Before | After |
| --- | --- | --- |
| Sairedis `//:runtime_packages.json` after a kernel-tool disk-cache hit | Default downloading reproduced a missing Perl `5.40/machine` alias | Targeted downloading preserved the tool tree and generated metadata identical to the cold build |
| Relocated `dpkg-shlibdeps` library ownership lookup | `/lib` aliases could hide canonical package ownership | Canonical `/usr/lib/<multiarch>` lookup remains first |

The [native cache experiment](https://github.com/securely1g/sonic-build-infra/actions/runs/40080628232)
verified the first row on AMD64 and ARM64 without directory normalization.
That experiment is supporting evidence, not validation of this new registry head.

## Validation and publication

The registry configuration retains all 29 build targets and 26 test targets
from the preceding candidate on native AMD64 and ARM64. This includes compiler,
runtime, stripping, debug, generated metadata and complete-control regressions.
Registry wrappers execute the original AMD64-to-ARM64/ARMHF cross-tool tests on
AMD64 and the native kernel regression on ARM64. The only source patches update
the module version and expose those existing tests for consumer validation.

All published entries, including `0.0.20-b2aee6e323cf193fc7a034e2c5f71a3fd04e4160`
and `0.0.21-b541569502affaf04befe9596969f3d74b979ad6`, remain unchanged.
This is the sole unpublished build-infra candidate in this stack. Its `0.0.22`
release prefix sorts above those published versions during Bazel resolution.
Fresh native registry validation is required before this candidate is complete.
