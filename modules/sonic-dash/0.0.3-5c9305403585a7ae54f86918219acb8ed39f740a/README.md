# DASH runtime metadata from its Debian recipe

Register the landed [DASH #2](https://github.com/securely1g/DASH/pull/2) implementation at `5c9305403585a7ae54f86918219acb8ed39f740a`. The source owns all build and metadata behavior; the registry applies only `patches/0001-bump-version.patch` to set the module version. Version `0.0.2` follows the published `0.0.1-97c07d05193e346bc990e816e30a7e3d72e8f4c0` entry, which remains unchanged.

[Syncd VS in buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13) maps `libsai` to `@sonic_dash//:runtime` and needs its package identity and dependencies alongside the TAR. The generated `@sonic-dash//:runtime_packages.json` reads the existing `dash-pipeline/SAI/debian/libsai_1.0.0_amd64/DEBIAN/control` and analyzes the actual runtime libraries with the declared PI/APT metadata. The package version remains `1.0.0`; the record includes the target architecture and exact runtime TAR hash. This registry version exposes that landed implementation; consumer adoption is separate work.

| Input or action | Published source registration | This registration |
| --- | --- | --- |
| Build `@sonic-dash//:runtime_packages.json` | No metadata target. | Generates the `libsai` package record from the existing control and runtime TAR. |
| Build on native ARM64 with the legacy AMD64-named control path | Runtime and SDK are ARM64, but there is no generated package record. | Validates the ELF architecture and records `arm64`. |
| Analyze SDK consumers that link protobuf-lite | Its already-selected Debian payload/control is not exported by the metadata provider. | Exposes `libprotobuf-lite32t64` from the same pinned Debian dependency set. |

Native AMD64 and ARM64 presubmits retain the published runtime, matching debug TAR and SDK builds and `@sonic-dash//bazel:runtime_test`, then add the generated metadata target. They cover installed SDK use, pipeline outputs, independent loading, ELF closure, matching debug symbols and GDB source lookup. Both host and target use the declared Trixie toolchain. The shared runner retains source, module resolution, build/test and complete output-tree evidence.

Selected build infrastructure `0.0.22-a12bc826d6f811a157db5c7c02a2fe033896cc14`, PI, P4C, `rules_foreign_cc` and `rules_distroless` recipes are published on canonical registry `main`. No temporary registry override or new DEB producer is added. These producer checks do not establish a full Syncd image, boot or forwarding test.
