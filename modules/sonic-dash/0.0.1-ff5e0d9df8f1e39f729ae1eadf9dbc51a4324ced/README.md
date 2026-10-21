# DASH runtime package metadata

Register [DASH #2](https://github.com/securely1g/DASH/pull/2), which keeps the source-owned `libsai` package identity, version and runtime dependency list beside the runtime TAR. [Buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13) consumes `//:runtime_packages.json` with the matching runtime TAR and selected module; it does not need a Debian package build or an image-local copy of the package fields.

The metadata describes the corrected source library's verified PI, gRPC, protobuf, Abseil and standard runtime dependencies. The exact versions come from the declared module and Trixie APT inputs. It preserves legacy Make and Debian control files. Native AMD64 and ARM64 presubmits retain the metadata and all runtime/debug/SDK outputs and run the same independent loader, generated pipeline, SDK, ELF closure and debug-symbol tests as the underlying source registration.

This Draft PR is one metadata-registration commit above [registry #94](https://github.com/securely1g/sonic-bazel-registry/pull/94). Direct merge gates are that source registration and DASH #2. Its inherited source/shared prerequisites must land first; then repin to landed source, retarget maintained main and repeat both native consumer jobs before Ready.
