# BMv2 from the maintained SONiC source

This module builds the BMv2 `1.15.0-9` source used by SONiC's P4 image. Bazel
fetches the checksum-verified original archive and Debian source archive, applies
Debian's `fix-distclean.patch`, then SONiC's `0001-use-boost-1.83.patch`
and `0002-remove-unnecessary-dependencies.patch` in that order. It invokes
upstream Autotools/Make through
`rules_foreign_cc.configure_make`. It does not build Debian packages or change
SONiC's existing Make recipes.
The registry also patches the Thrift version check to read the target
`thrift/config.h` with the C++ compiler. Native builds and ARM64 cross-builds
use the header version to select the same Thrift interfaces.
The configure-flags test uses the foreign build tools for the execution platform,
as the configure action does. The package test loads and exercises the target
programs and libraries.

The configured features match the maintained recipe: PDFixed, Thrift, nanomsg,
PI and `simple_switch_grpc`. PI headers/libraries come from the independently
source-built `p4lang-pi` SDK. Target libraries come from declared Trixie APT
inputs. Autotools, Python and protocol generators come from the declared build
infrastructure execution-tool bundle. No configure/build action downloads code.

## Public targets

| Target | Purpose |
| --- | --- |
| `:runtime` | Stripped programs, shared libraries, Python clients and licenses in their installed paths |
| `:runtime.debug_symbols` | Build-ID debug files split from those same linked ELF files |
| `:sdk` | Installed headers and libraries with CcInfo for source consumers such as DASH |
| `:package_test` | Installed programs, SDK consumer, enabled features, SONAMEs and matching debug symbols |
| `:config_log`, `:grpc_config_log` | Configure evidence retained by CI |

The runtime installs `simple_switch`, `simple_switch_grpc`, `psa_switch` and
`pna_nic`, eleven shared libraries and their SONAME links, the upstream Python
Thrift/protobuf clients, and command helpers. Development headers and static
libraries are SDK build inputs rather than OCI payloads. Container consumers
also include PI's runtime and the declared target-library runtime closure.

Use both runtime and debug TARs directly with OCI rules; there is no intermediate
DEB conversion. `sonic_deploy_tar(force_debug_build = True)` keeps compilation
symbols until splitting the final artifacts. The test checks build IDs and
debuglink CRCs for every deployed ELF and GDB source-line lookup after adding the
debug TAR. Native AMD64 and ARM64 jobs run the independent registry consumer.

```sh
python3 ci/registry_ci.py run --module p4lang-bmv2 --version 1.15.0.sonic.4 \
  --architecture amd64 --work-dir /tmp/bmv2-amd64 --artifacts /tmp/bmv2-artifacts
```

Replace `amd64` with `arm64` on an ARM64 host. The package test does not exercise
privileged packet forwarding or the upstream network integration suite. Foreign
Make compilation is one Bazel action per configured build, so this integration
does not provide per-source-file Bazel compilation caching.

## Provenance

Original archive SHA256:
`083bb907e45597af8e29ef3b0a92d33d282ba23840ddd5cfb8372d2f030ab415`.
Debian source archive SHA256:
`30941da6dde4cbbefaa9a12dfffa260115b3b63c6d56b3112b3baee953636179`.
The source archives supply Debian patches and copyright metadata; the overlay
contains only the maintained SONiC patches and Bazel integration.
The archive identifies upstream revision
`68f4a978f465fd76e98fcdecb762981843fb7310`; a generated `VERSION-build` preserves
that version suffix without running Git inside a build action.

The BCR has no `bmv2`, `behavioral-model` or `p4lang-bmv2` entry. The imported
archive has an Autotools build and no upstream Bazel module.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.

## Large native include and linker lists

Gearbox image PR #154 selects the complete PI/BMv2 dependency closure. Its
native AMD64 debug action produced a 141,742-byte `CPPFLAGS` environment entry.
Linux rejects a single environment string above 131,072 bytes, so `/bin/sh`
could not start BMv2's configure adapter. The compiler launcher could not help
because the failure occurred before it ran.

This version uses the public `configure_prefix` with the shell's `source`
builtin. It writes the ordered preprocessor arguments to a private GCC response
file before starting a process and forwards that file directly to the
preprocessor. The original final native include directory remains last in that
same list. Configuration options, optimization/debug flags, source archives,
patches, installed paths and source ownership remain unchanged.

`//:configure_flags_test` reproduces the original pre-exec failure with a larger
include list, then exercises the real owner configure frontend, GNU Autoconf
C/C++/preprocessor checks and recursive Make in the same shell. It checks quoted
macros, spaces in include paths, header precedence, rejection of driver-only
CPPFLAGS and exact equality of short/long executable bytes. This focused native
Trixie test passed locally; complete package and downstream image acceptance are
separate gates and are still pending for this candidate.


The standalone DASH Engine image exposed the remaining linker limit: its
136,826-byte `LDFLAGS` exceeded Linux's per-string limit before GCC started.
The same configure prefix now stores its shell-parsed linker arguments in the
private `.sonic-linker-arguments` vector. The existing shared compiler launcher
expands only that exact vector before shortening absolute library searches for
each recursive working directory. Every flag and library-search order remains
intact; arbitrary GCC response files stay opaque.

This requires the source launcher from
[sonic-build-infra PR #82](https://github.com/securely1g/sonic-build-infra/pull/82),
registered as `0.0.27-08e0956f80574b27a9b68e72fe855cc0089058e5`. Both the module
minimum and the independent consumer select that version. No source archive,
source patch, target ABI, configured feature or installed path changed.

The extended original test covers both pre-exec failures and real C/C++ links
through Autoconf and recursive Libtool, including quoted paths, competing
libraries and exact short/long executable bytes. Local regression and the exact
338-argument Engine-vector diagnostic pass. The earlier AMD64/ARM64 acceptance
belongs to the previous candidate; updated registry CI and Engine acceptance
remain pending. The original six build targets and two tests on both native
architectures are preserved, with no DEB generation.

Both native registry builds at `29f27a3` reached the `simple_switch_grpc` link,
then could not locate four libraries required by PI's `libpifeproto` and
`libpigrpcserver`. PI already exports their SONAME files in the declared SDK.
BMv2 now includes that SDK's `lib` directory in its existing link-time
`rpath-link` search, in addition to the imported-library directory. This does
not add a runtime search path or change PI's library declarations. Source
archives, patches and both architecture target inventories are unchanged.
The failed build retained the configured flags and linker diagnostics, but
upstream `V=0` omitted the expanded final link command. Corrected native
registry and downstream Engine acceptance remain pending.
