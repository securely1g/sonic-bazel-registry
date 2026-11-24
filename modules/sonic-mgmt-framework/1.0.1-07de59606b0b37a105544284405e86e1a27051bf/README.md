# Native Framework CLI

This version pins Framework source `07de59606b0b37a105544284405e86e1a27051bf` and supplies the native
CLI adaptation from this registry. No Framework source-repository change is required.

The klish source repository is prepared by the existing Infra `prepared_source`
rule. Native `cc_library`, `cc_shared_library`, and `cc_binary` targets compile
the original patched source set. Normal builds generate the configuration header
from the reviewed AMD64/Trixie template and invoke no configure or Make process.

Existing REST, model and CLI asset generators, runtime/debug TAR targets, installed
paths, SONAMEs, and static library interfaces are preserved. Dependency versions
match the pinned Framework source and the previously validated native implementation.

The independent consumer selects this exact version and reads the Framework Go
workspace; the fetched module contributes its own `go.mod`, preserving registry
Go ownership. The presubmit retains the published seven build and ten test targets.
