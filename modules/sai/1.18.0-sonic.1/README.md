# SAI 1.18.0-sonic.1

This first registry revision moves the reusable SAI dependency support from
[sonic-sairedis PR #1](https://github.com/securely1g/sonic-sairedis/pull/1)
into one dependency module. The consumer no longer needs its own source archive,
header overlay, metadata generator, Aspell patch, or generator tool lock.

## Source and version

The upstream `inc/saiversion.h` defines SAI **1.18.0**. This entry deliberately
keeps sonic-sairedis's source snapshot
`6dd738196ebb267be458eed0a00b687568455914`: it is **32 commits after** release tag
`v1.18.0` (`4b4347b59397c462b804da2ccd7784214406477a`), not the release archive.
[`upstream-changes.json`](upstream-changes.json) lists the exact intervening
commits, including the final ACL entry label change. The `-sonic.1` revision
represents this snapshot and its downstream Bazel overlay/patch set.

The source archive SHA256 is
`c3245b27beee0d3d73531a9c5ffcb0473ff5fea9b32124954c25a50cb5e56750`.
`SOURCE_PROVENANCE.json`, `attribute_versions.json`, and `MODULE.bazel` are
public inputs for consumer provenance checks. The attribute-version header
and its ordered tag history are carried forward unchanged from the existing
sairedis build; regeneration instructions are in `attribute_versions.json`.

## Public targets

| Target | Contract |
| --- | --- |
| `:headers` | Public/custom/experimental and metadata headers, including generated `saimetadata.h` |
| `:upstream_headers` | Original API and metadata support headers without running generation |
| `:metadata` | Four declared generated outputs: C source/header, metadata test C source, SWIG interface |
| `:saimetadata_c`, `:saimetadata_h`, `:saimetadatatest_c`, `:saiswig_i` | Individual generated outputs |
| `:saiattrversion_h` | Attribute-version history header |
| `:api_header_files`, `:metadata_header_files` | Files for consumer development packages |
| `:metadata_support_sources` | Upstream metadata utilities and serializer C source |
| `:metadata_library` | Static metadata library for consumers choosing this boundary |
| `:stub_inputs` | Original API headers for consumer-specific entry-stub generation |
| `:generator_inputs` | Complete source inputs to upstream metadata generation |
| `:inc/sai.h`, `:meta/parse.pl`, `:meta/saiattrversion.h`, `:LICENSE.txt` | Stable exported upstream paths |

The metadata rule and Python launcher live with this third-party dependency.
The generator uses declared Perl/Python runtimes and Doxygen, Aspell, and
English dictionaries resolved by `sonic-build-infra`'s separate `build_tools`
APT package set. It consumes the three package targets and their transitive
runtime payloads. The compiler `sysroot` set stays separate, and the shared
Debian snapshots preserve the previously validated generator versions.

Tool preparation reproduces Aspell's dictionary setup and rejects undeclared
library resolution. The metadata action selects this bundle in the execution
configuration; its CPU follows the machine running the generator. No host
`PATH`, `/usr/bin/aspell`, or network access is required by generation.
Package resolution and downloads belong to build-infra/rules_distroless;
SAI keeps only its generator-specific preparation and metadata rules.

Sairedis's Redis/VS/proxy stub implementation, runtime SONAMEs, deployment/debug
packages and integration tests remain in sairedis. No service runtime, vendor
SAI backend, Debian binary package, ARMHF support or container image is claimed
by this dependency module.

## Validation

`presubmit.json` runs the existing registry consumer workflow on native AMD64
and ARM64 Debian Trixie workers with Bazel 8.5.1. It pins shared infrastructure
`0.0.8-e8b05b109187345586a18628ad01626e69c02fbe` for the test environment.

- Build the required metadata outputs and a C consumer linked to the metadata
  support library; query real PORT metadata through the exported SAI API.
- Verify all four generated outputs plus the attribute-version header against
  SHA256 hashes from the retained sonic-sairedis PR #1 baseline. This protects
  the existing generated-byte contract while ownership moves to the registry.
- Run both tests uncached and retain generated outputs, native test binary,
  fetched module identity, logs and test reports as workflow artifacts.

The registry tests verify this module independently. Sairedis's native build,
package, detached-symbol and service-free regression checks validate its use
of the module separately.

The shared package source is [build-infra #8](https://github.com/securely1g/sonic-build-infra/pull/8),
published by [registry #22](https://github.com/securely1g/sonic-bazel-registry/pull/22).
Registry #22 must be available in the consumer's registry snapshot before this
SAI version can resolve its shared infrastructure dependency.
