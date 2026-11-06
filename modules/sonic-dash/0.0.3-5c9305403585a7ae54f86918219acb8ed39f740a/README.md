# DASH runtime metadata from its Debian recipe

Version `0.0.3` uses DASH commit `5c9305403585a7ae54f86918219acb8ed39f740a`, the same source archive as the `0.0.2` recipe. The registry patch sets the module version and selects PI `0.1.3.sonic.3` and P4C `1.2.4.2.sonic.3` for cross-compilation. [Upstream DASH change](https://github.com/securely1g/DASH/pull/2)

[Syncd VS in buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13) maps `libsai` to `@sonic_dash//:runtime` and needs its package identity and dependencies alongside the TAR. The generated `@sonic-dash//:runtime_packages.json` reads the existing `dash-pipeline/SAI/debian/libsai_1.0.0_amd64/DEBIAN/control` and analyzes the actual runtime libraries with the declared PI/APT metadata. The package version remains `1.0.0`; the record includes the target architecture and exact runtime TAR hash. This registry version exposes that landed implementation; consumer adoption is separate work.

| Input or action | Published source registration | This registration |
| --- | --- | --- |
| Build `@sonic-dash//:runtime_packages.json` | No metadata target. | Generates the `libsai` package record from the existing control and runtime TAR. |
| Build on native ARM64 with the legacy AMD64-named control path | Runtime and SDK are ARM64, but there is no generated package record. | Validates the ELF architecture and records `arm64`. |
| Analyze SDK consumers that link protobuf-lite | Its already-selected Debian payload/control is not exported by the metadata provider. | Exposes `libprotobuf-lite32t64` from the same pinned Debian dependency set. |

The AMD64 and ARM64 presubmits build the runtime, matching debug TAR, SDK and package metadata. The original `@sonic-dash//bazel:runtime_test` covers installed SDK use, pipeline outputs, independent library loading, ELF dependencies, debug symbols and GDB source lookup.

DASH declares the Trixie toolchain from `sonic-build-infra` version `0.0.22-a12bc826d6f811a157db5c7c02a2fe033896cc14`. Bazel builds P4C for the execution platform so its compiler can generate the pipeline during an ARM64 cross-build.