## Dependency refresh for `0.6.1.sonic.1`

This candidate retains the `0.6.1.sonic-buildimage` source and existing patches. Its module dependencies select the newest non-yanked versions published at `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. Versions introduced by this refresh are not dependency targets of the same refresh.

The AMD64 integration consumer builds the upstream `types_cc_proto` target and
serializes a public gNOI `Path` message, then parses it and checks its origin and
interface key. This checks the generated C++ API and its linked protobuf runtime
from a separate module. The registry entry previously had no presubmit recipe.

`overlay/MODULE.bazel` is generated from the canonical module declaration with
`python3 ci/registry_ci.py sync-module --module com_github_openconfig_gnoi --version 0.6.1.sonic.1`.

