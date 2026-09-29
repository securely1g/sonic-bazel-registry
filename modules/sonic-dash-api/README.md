# SONiC DASH API

`0.0.0-7af4056f7393b2ccbca9fc2d9aa668251e55b0a7` publishes the
source-owned Bazel import from
[`securely1g/sonic-dash-api` commit `7af4056`](https://github.com/securely1g/sonic-dash-api/commit/7af4056f7393b2ccbca9fc2d9aa668251e55b0a7).
The source snapshot is based on the existing package producer commit
`2ce7ce648ee77a76fcf567191eb4b9ed6cfeed38`. The only registry patch sets
the module version.

Consumers declare the module with a local repository name:

```starlark
bazel_dep(
    name = "sonic-dash-api",
    version = "0.0.0-7af4056f7393b2ccbca9fc2d9aa668251e55b0a7",
    repo_name = "sonic_dash_api",
)
```

The public C++ target is `@sonic_dash_api//:dashapi`. It exports the
`dash_api` headers and imports `libdashapi.so` from the existing Trixie input
DEB selected for the target CPU. It does not add a protobuf dependency to the
public C++ interface, so SWSS retains its current protobuf selection.

## Pinned package inputs

The source module records the public Azure artifact URLs, exact ZIP members,
producer build and source commit, package identity, and SHA256 values in
`bazel/prebuilt.json`. These are the package bytes already selected by SWSS:

| Native CPU | Input package | SHA256 |
| --- | --- | --- |
| AMD64 | `libdashapi_1.0.0_amd64.deb` | `93c02c0394b3e20660e9364f0442321207a4d13f776849ba71faf58e32a25d8d` |
| ARM64 | `libdashapi_1.0.0_arm64.deb` | `a48b68829f8a083d1997073b24a21ed948b2b6fd2d1230ba17f424d2b4194471` |

The importer downloads the recorded public ZIP, selects the recorded member,
checks the DEB hash, and extracts the headers and library. No package is built
by this module.

## Native registry validation

The presubmit creates an external consumer on native Debian Trixie AMD64 and
ARM64. It explicitly requests infrastructure
`0.0.7-91fe8246519f99838da936eee54e85208c704a4d`, builds the selected files and
C++ consumer, and runs both source-owned tests uncached:

- `//bazel:prebuilt_contract_test` checks the DEB identity and hash, exported
  file bytes, ELF machine, and protobuf runtime dependency against the manifest.
- `//bazel:runtime_consumer_test` calls the imported C and C++ interfaces,
  performs a protobuf round trip, and confirms the loaded library is the
  selected import. Its test-only Debian dependency set uses the existing
  `libprotobuf-dev:libprotobuf` C++ target.

The source import supplies `//:prebuilt_files` for consumers that need the
original DEB, exported files, and import record. This stack uses registry
PR #4's existing runner, which retains test evidence but does not retain the
selected build outputs or a fetched infrastructure declaration. The downstream
SWSS validation must record its resolved dependency graph separately.

The source prerequisite is
[sonic-dash-api PR #1](https://github.com/securely1g/sonic-dash-api/pull/1), and
the infrastructure entry is supplied by the explicit
[registry PR #4](https://github.com/securely1g/sonic-bazel-registry/pull/4)
stack base. This registration validates the import boundary; it does not build
a DASH package or a SONiC image.
