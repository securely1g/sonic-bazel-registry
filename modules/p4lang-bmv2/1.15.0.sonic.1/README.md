# BMv2 from the maintained SONiC source

This module builds the BMv2 `1.15.0-9` source used by SONiC's P4 image. Bazel
fetches the checksum-verified original archive and Debian source archive, applies
Debian's `fix-distclean.patch` followed by SONiC's Boost 1.83 and unnecessary
dependency patches, and invokes upstream Autotools/Make through
`rules_foreign_cc.configure_make`. It does not build Debian packages or change
SONiC's existing Make recipes.

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
python3 ci/registry_ci.py run --module p4lang-bmv2 --version 1.15.0.sonic.1 \
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
