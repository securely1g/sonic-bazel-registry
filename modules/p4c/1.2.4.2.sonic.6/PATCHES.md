# P4C patch provenance

Compiler source: p4lang/p4c commit `624c6be8076881e9af1e2f7d7691bc6c4416f4b1`. Apply the retained Debian series followed by the patches declared in `MODULE.bazel`.

| Patch | Source and purpose |
| --- | --- |
| `0001`–`0005` | Original SONiC Boost 1.83, Thrift and packaging dependency patches. |
| `0007-recognize-driver-include-directory.patch` | Relocated compiler-tool adaptation: recognize the original single-directory driver include variables after the executable-relative search, retaining the preprocessor's path spelling. |

Native actions replace CMake execution-generator setup. Compiler semantics and upstream regression expectations remain unchanged.
