# SAI 1.18.0-sonic.1

This first registry revision moves the reusable SAI dependency support from
[sonic-sairedis PR #1](https://github.com/securely1g/sonic-sairedis/pull/1)
into one dependency module. The consumer no longer needs its own source archive,
header overlay, metadata generator, or generator tool lock. Upstream SAI source
is used without patches.

This registration lets Bazel download SAI source and build its public headers,
generated metadata, and optional static metadata library. It does **not**
provide an installable SAI `.deb` package. The generator runs in a shared build-tools container published by
`sonic-build-infra` and pinned by its final image digest. Aspell, English
dictionaries, and Doxygen are installed at their normal system paths. Sairedis consumes the SAI targets and owns its
runtime/development/debug packages, shared-library ABI, and Redis/VS backends.
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
`SOURCE_PROVENANCE.json`, `attribute_versions.json`, and `MODULE.bazel` are
public inputs for consumer provenance checks. The attribute-version header
and its ordered tag history are carried forward unchanged from the existing
sairedis build; regeneration instructions are in `attribute_versions.json`.

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

### Build-tools execution container

SAI's original spell checker invokes `/usr/bin/aspell`. The shared container
installs Aspell and English dictionaries with Debian's normal package setup,
so the original `meta/style.pm` works without `declared_aspell.patch`. The
custom Debian payload extraction, dynamic-loader wrapper, and dictionary
preparation script have been removed. Spell checking remains enabled.

[`overlay/bazel/tools.bzl`](overlay/bazel/tools.bzl) pins the completed
multi-platform image and its recipe hash. AMD64 and ARM64 execution toolchains
use that same image index; the container runtime selects the native image.
Compiler target sysroots remain separate. Python and Perl retain their declared
Bazel execution runtimes.

The metadata target declares the pinned `container-image` execution property
for a compatible remote executor. Its action also includes the image and recipe
in its arguments, so changing either changes the action cache key. Generation
checks `/etc/sonic-build-tools.json` for the expected recipe and execution
architecture, rejecting a host or wrong-recipe environment before running
Doxygen. The marker checks the environment contract; the Docker launcher or
remote executor enforces the image digest. Bazel's ordinary local sandbox does
not start Docker from `exec_properties`.

For local builds, run the entire Bazel invocation inside the exact image listed
in [`presubmit.json`](presubmit.json), using the shared [build-tools container launcher](https://github.com/securely1g/sonic-build-infra/blob/731694bc809ba8ac3b8e50f2276e1d76b6c751ed/containers/build-tools/run.sh). Use the matching `SONIC_BUILD_TOOLS_IMAGE` and
`SONIC_BUILD_TOOLS_RECIPE` action environment settings for other container tools.
Registry CI selects that same pinned image, checks its marker and native
architecture, and records the image identity with the generated artifacts.

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
declared files. Tool installation and image publication belong to build-infra;
SAI owns only its toolchain selection and metadata invocation. Generation does
not download or install packages.

Sairedis's Redis/VS/proxy stub implementation, runtime SONAMEs, deployment/debug
packages and integration tests remain in sairedis. No service runtime, vendor
SAI backend, Debian binary package, ARMHF support or runtime container image is claimed
by this dependency module.

## Validation

`presubmit.json` runs the existing registry consumer workflow on native AMD64
and ARM64 workers inside the pinned Debian Trixie tools container with Bazel 8.5.1. It pins shared infrastructure
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

The shared compiler infrastructure is [build-infra #8](https://github.com/securely1g/sonic-build-infra/pull/8),
published by [registry #22](https://github.com/securely1g/sonic-bazel-registry/pull/22).
Registry #22 must be available in the consumer's registry snapshot before this
SAI version can resolve its shared infrastructure dependency.

The execution image is published by [build-infra #12](https://github.com/securely1g/sonic-build-infra/pull/12).
[Registry #26](https://github.com/securely1g/sonic-bazel-registry/pull/26) adds the
pinned-image presubmit configuration. This module PR is stacked on that CI PR
so its native checks run with the same container contract.
