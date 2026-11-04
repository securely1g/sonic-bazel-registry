# Runtime package metadata

`//:runtime_packages.json` is generated from the upstream Debian control and
changelog plus the actual `//:libyang_pkg` runtime TAR. The shared producer
computes target ELF dependencies using declared APT libraries and target ABI
packages, validates `usr/lib/{multiarch}/libyang.so.3`, and binds the controls to
the payload SHA256. It exports target architecture and required paths for the
shared OCI consumer. Source package identity and version stay in the recipe.

OCI consumers use the runtime TAR, matching `.debug_symbols` target, this
metadata and the selected MODULE declaration. The shared owner-metadata consumer
merges producer path requirements with image-specific requirements, verifies
module/target identity and carries the payload binding to image validation.
`runtime_metadata_test` exercises that consumer with real generated inputs.

This metadata interface supports Trixie AMD64 and ARM64. Image assembly owns
accounts, services, caches and configuration. Runtime and tool TAR targets also
support their declared Bookworm platforms.
