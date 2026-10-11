# Prefer concrete APT packages

This revision keeps the upstream rules_distroless 0.9.4 source archive and all
four production fixes from `0.9.4.sonic.4`: include fragments, pkg-config
whitespace, multiarch headers and public pkg-config files. Released and earlier
candidate entries are unchanged.

The additional resolver patch is owned by
[sonic-build-infra #42](https://github.com/securely1g/sonic-build-infra/pull/42),
source commit `12a67fd2bc292af156f40372274c9cb3011e5c23`, at
`third_party/rules_distroless/0001-concrete-packages.patch`. Its bytes are copied
unchanged here and integrity pinned alongside the prior patches.

A package requested by its own name is selected before virtual providers when
it satisfies the requested version, architecture and suite. If no concrete
candidate matches, the existing virtual-provider fallback still applies. For
example, `vim (= 2:9.1.1230-2)` selects concrete Vim instead of vim-nox, allowing
Syncd's debug image to install its matching original control metadata and data.
This changes upstream resolution behavior; it introduces no new importer.

Native AMD64 and ARM64 consuming-module presubmits retain every previous header,
architecture and pkg-config check. The added regression uses the real index
parser and resolver with sixteen cases across both architecture records,
including virtual-only, version/suite fallback and Architecture: all packages.
The unchanged upstream resolver fails the same concrete-package checks. Tests
import existing package payloads or resolve metadata; none produces a DEB.

This registration is Draft while its source patch and prerequisite registry
[#63](https://github.com/securely1g/sonic-bazel-registry/pull/63) are unlanded.
