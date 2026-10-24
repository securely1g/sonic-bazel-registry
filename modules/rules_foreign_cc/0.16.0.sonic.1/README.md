# Preserve dependency header classes in foreign Make builds

The upstream Make/configure adapter emits dependency header paths as `-I`.
That changes quote-header lookup and exposes vendor-header warnings to DASH's
`-Werror`. This version preserves the classes already carried by `CcInfo`:
`-iquote`, `-I` and `-isystem`. Installed foreign SDK paths still point to the
declared staging tree. Library order, CMake staging and compiler selection are
unchanged. The source remains the exact upstream 0.16.0 release archive; the
other patch changes only its module version.

The direct consumer is [DASH #1](https://github.com/securely1g/DASH/pull/1)'s
source-built SAI libraries. [Buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13)
consumes their runtime/debug TARs for OCI. This entry creates no Debian packages.

## Upstream and approval

On 2026-10-21, the latest BCR version and upstream release were 0.16.0. Upstream
main at `4f2b79acb31daa912447151eec5fc29ac49a17c4` still flattened these classes
in `foreign_cc/private/make_env_vars.bzl`. A review of all 54 open PR file lists
and diffs, plus five relevant closed PRs, found no matching fix.
[PR #1470](https://github.com/bazel-contrib/rules_foreign_cc/pull/1470) and
[PR #1603](https://github.com/bazel-contrib/rules_foreign_cc/pull/1603) concern
bootstrap compiler flags, rather than dependency header classes. The user
explicitly approved this patched registry version and native AMD64/ARM64
validation on 2026-10-21. Upstream definitions and attribution are preserved.

## Validation

The registry consumer uses declared Debian Trixie GCC14 and packaged Make, M4
and pkg-config. Its fixture-only tool settings must be supplied; omission
fails analysis instead of selecting ambient tools. The published module has
no production dependency on SONiC infrastructure.

Native tests build actual Make and CMake fixtures and a produced SDK. They
check system-warning treatment, ordinary warnings remaining errors, quote
lookup precedence, quote-only angle exclusion, missing-directory diagnostics
and staged SDK aliases. A local byte-identical upstream-core control fails
the expected vendor/SDK unused-parameter warnings. Mixed-version resolution
selects this version over upstream 0.16.0 without a module override.

Both native architectures are selected in `presubmit.json`; hosted results
are recorded in the PR. The temporary registry base supplies the fixture
toolchain through [registry #118](https://github.com/securely1g/sonic-bazel-registry/pull/118).
Keep the PR Draft until that dependency lands, then retarget the maintained
registry branch and validate again.
