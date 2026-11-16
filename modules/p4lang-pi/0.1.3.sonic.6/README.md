# PI 0.1.3 native SONiC adaptation

This module builds the fixed `p4lang-pi 0.1.3-2` source archive with native
Bazel C/C++ rules and explicit protobuf/gRPC generation. The SONiC entry enables
proto, CLI and the C++ frontend. BMV2, internal RPC and sysrepo stay disabled.

The shared infrastructure supplies the pinned Trixie `pi_deps` libraries and
execution tools. Source preparation preserves the original Debian metadata and
ordered SONiC patches. Original upstream Bazel package boundaries are removed
so the native module owns its source and generated-code declarations.

## Public interfaces

- `:sdk` and the original individual library targets export native CcInfo.
- `:p4lang-pi.runtime` installs the original twelve shared libraries, four
  programs and generated Python bindings under `/usr`.
- `:p4lang-pi.runtime.debug_symbols` contains matching native debug symbols.
- `:development` installs the public headers, static archives and development
  library links.
- `:p4lang-pi.runtime_metadata` derives package metadata from the fixed Debian
  control/changelog and the actual runtime TAR.
- `:upstream_tests` preserves the original eighteen default tests;
  `:check_programs` also builds the original build-only checks and examples.

The runtime and debug interfaces select the AMD64 or ARM64 installation layout
from the target platform. Historical `:runtime`, `:runtime.debug_symbols` and
`:runtime_packages.json` labels remain aliases because published BMv2 and DASH
modules consume them. No configure or Make action participates in compilation.

## Validation commands

From the registry checkout, synchronize the generated module overlay:

```sh
python3 ci/registry_ci.py sync-module --module p4lang-pi --version 0.1.3.sonic.6 --check
```

Run each architecture in its native Trixie environment with a new empty work
directory and an artifacts directory outside it:

```sh
python3 ci/registry_ci.py run --module p4lang-pi --version 0.1.3.sonic.6 --architecture amd64 --work-dir /tmp/pi-native-amd64-work --artifacts /tmp/pi-native-amd64-artifacts
python3 ci/registry_ci.py run --module p4lang-pi --version 0.1.3.sonic.6 --architecture arm64 --work-dir /tmp/pi-native-arm64-work --artifacts /tmp/pi-native-arm64-artifacts
```

These commands define the validation entry points; their results are recorded
separately for the exact candidate inputs.

## Upstream test runtime

The existing 18 upstream tests use the registry `test_runtime_preparation` protocol in a Debian Trixie test container. The component preparation script selects the runtime closure from the shared production APT lock, verifies original package hashes, and retains the base image package versions. The public BUILD targets and their arguments remain unchanged.
