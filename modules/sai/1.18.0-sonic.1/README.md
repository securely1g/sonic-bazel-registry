# SAI 1.18.0-sonic.1

This first registry revision moves the reusable SAI dependency support from
[sonic-sairedis PR #1](https://github.com/securely1g/sonic-sairedis/pull/1)
into one dependency module. The consumer no longer needs its own source archive,
header overlay, metadata generator, or generator tool lock. One small source
patch makes the Aspell executable configurable while preserving the Make default.

This registration lets Bazel download SAI source and build its public headers,
generated metadata, and optional static metadata library. It does **not**
provide an installable SAI `.deb` package. The generator consumes pinned Aspell
and Doxygen launchers from `sonic-build-infra`, including their runtime libraries
and initialized English dictionaries. Sairedis consumes the SAI targets and owns
its runtime/development/debug packages, shared-library ABI, and Redis/VS backends.
For example, `@sai_source//:metadata` generates the metadata files and
`@sai_source//:metadata_library` builds a linkable static library when the
consumer uses `repo_name = "sai_source"`.

## Source and version

The upstream `inc/saiversion.h` defines SAI **1.18.0**. This entry deliberately
keeps sonic-sairedis's source snapshot
`6dd738196ebb267be458eed0a00b687568455914`: it is **32 commits after** release tag
`v1.18.0` (`4b4347b59397c462b804da2ccd7784214406477a`), not the release archive.
[`upstream-changes.json`](upstream-changes.json) lists the exact intervening
commits, including the final ACL entry label change. The `-sonic.1` revision
represents this snapshot and its downstream Bazel overlay.

The source archive SHA256 is
`c3245b27beee0d3d73531a9c5ffcb0473ff5fea9b32124954c25a50cb5e56750`.
`SOURCE_PROVENANCE.json` and `MODULE.bazel` supply the source and module
identities checked by Sairedis's package verifier. `attribute_versions.json`
records the ordered tag history, expected header hash, and regeneration steps
for maintainers. It is exported with the module but is not consumed by the
current build actions or Sairedis's package verifier. The attribute-version
header and its tag history are carried forward unchanged from the existing
sairedis build.

### Why the attribute-version header is checked in

[`overlay/meta/saiattrversion.h`](overlay/meta/saiattrversion.h) records the SAI
release that first introduced each attribute (or `HEAD` for a future release).
Upstream `meta/parse.pl` reads it in `ExtractAttrApiVersion` and uses
`ProcessApiVersion` to populate generated attribute metadata. Missing version
information falls back to `SAI_VERSION(0,0,0)`, changing that metadata contract.
Sairedis also installs the header as `usr/include/sai/saiattrversion.h` in its
development payload.

The upstream `meta/attrversion.sh` generator walks Git tags from `v1.10.0`
onward. The source archive used by Bazel has no `.git` directory or tags;
running that script there produces an empty header. Carrying the generated
header with an explicit ordered-tag manifest makes this build independent of
live Git history and preserves Sairedis's existing output. The header is
byte-identical to
[`third_party/sai/saiattrversion.h` in Sairedis `6a6dd51`](https://github.com/securely1g/sonic-sairedis/blob/6a6dd51e9c9c09adf5c19086082940ff0fca2fb4/third_party/sai/saiattrversion.h).

The header is therefore a required input to the current metadata/package
contract, rather than a second SAI implementation. A future build-time
replacement would need the same complete, pinned tag history and output-parity
validation. The existing generated-output test checks its recorded SHA256
together with the four metadata outputs.

### Declared build tools and the Aspell path

Upstream `meta/style.pm` hardcodes `/usr/bin/aspell`. The
[`configurable_aspell.patch`](patches/configurable_aspell.patch) adds one optional
`SAI_ASPELL` executable path. When unset, the existing Make build still uses
`/usr/bin/aspell`. The executable receives the same language, personal-dictionary
and spelling-check arguments. Process invocation uses separate arguments, and
launch or process failures are reported as errors; spelling checks remain enabled.

The Bazel generator sets `SAI_ASPELL` to
`@sonic_build_infra//tools/build_tools:aspell` and invokes the matching `:doxygen`
launcher. Shared build infrastructure owns package extraction, ELF loader and
library selection, and dictionary preparation. SAI does not configure those
runtime details. Both tools are executable dependencies in execution configuration
(`cfg = "exec"`), with their complete runfiles declared as action tools. Updating
the tools or runtime inputs therefore changes the metadata action's inputs.
Compiler target sysroots remain separate. Python and Perl retain their declared
Bazel execution runtimes.

The generator runs in Bazel's ordinary action environment with an empty `PATH`;
it does not require a Docker image, container marker, chroot or installed host
Aspell/Doxygen. Registry CI can still use its standard Debian test environment.
The small source patch is a downstream adaptation, not a change accepted upstream.

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
All SAI sources remain declared inputs, and the generator produces exactly four
declared files. Tool preparation belongs to build-infra; SAI owns tool selection
and metadata invocation. Generation does not download or install packages.

Sairedis's Redis/VS/proxy stub implementation, runtime SONAMEs, deployment/debug
packages and integration tests remain in sairedis. No service runtime, vendor
SAI backend, Debian binary package, ARMHF support or runtime container image is claimed
by this dependency module.

## Validation

`presubmit.json` runs the registry consumer workflow on native AMD64 and ARM64
workers with Bazel 8.5.1. Its `consumer_deps` entry pins the shared infrastructure
version used by the module.

- Build the required metadata outputs and a C consumer linked to the metadata
  support library; query real PORT metadata through the exported SAI API.
- Verify all four generated outputs plus the attribute-version header against
  SHA256 hashes from the retained sonic-sairedis PR #1 baseline.
- Exercise configurable Aspell invocation, its default path, paths with spaces,
  argument and word forwarding, and failure propagation.
- Run tests uncached and retain generated outputs, the native test binary,
  fetched module identity, generated resolution lock, logs and test reports.

The registry tests verify this module independently. Sairedis's native build,
package, detached-symbol and service-free regression checks validate its use
of the module separately. Native AMD64 and ARM64 results do not establish
cross-compilation or remote-execution support.

The shared launcher registration must be available in the consumer's registry
snapshot before this SAI version can resolve its infrastructure dependency.

Shared launchers are implemented in [build-infra #13](https://github.com/securely1g/sonic-build-infra/pull/13)
and published as `0.0.13-f0bbc22fbce321d25aecafab4590fbfdbba59f85` by
[registry #27](https://github.com/securely1g/sonic-bazel-registry/pull/27).
This SAI PR is stacked on that registration. Its CI prerequisite
[registry #26](https://github.com/securely1g/sonic-bazel-registry/pull/26)
retains generated resolution locks as artifacts.
