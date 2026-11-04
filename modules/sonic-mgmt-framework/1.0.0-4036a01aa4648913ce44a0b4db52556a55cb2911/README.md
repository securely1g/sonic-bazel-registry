# Framework in the shared management Go graph

The registered Framework source remains 4036a01aa4648913ce44a0b4db52556a55cb2911.
Its production Go/C/Python source, generated-model recipe, REST compiler flags,
CLI recipe, Go locks and runtime/debug TAR contracts are unchanged. A separate
MODULE-only patch selects Management Common's cumulative shared-generator and
documentation source, plus the approved SONiC-patched public goyang/ygot modules.
It contributes go.mod requirements using the standard non-root Gazelle API.

The ordinary integration root uses gNMI's one existing go.bazel.work. It selects
glog 1.2.4, x/net 0.55.0, x/crypto 0.52.0 and x/sys 0.45.0, with Go 1.25.9 and
rules_go 0.65.0.sonic.1. These are deliberate shared dependency changes from the
older isolated Framework graph. The old pre-flag.Parse glog patch is not applied
to modern glog; unrelated JSON/XML/XPath and gNMI patches remain. Framework's
root-only legacy glog setting remains for its original standalone source use.

All seven output targets and five installed/code-generation tests remain. The
ordinary consumer also selects the five omitted existing source-CI suites, for
all ten original targets: REST server, OpenAPI generator, CLI client, CLI order,
TLS C++, installed REST/CLI, payload/symbols and model/codegen checks. Existing
host-authentication opt-in skips in the original REST suite are unchanged.

Current shared-graph native and installed-image acceptance is pending. Prior
4036 standalone acceptance is historical and does not establish compatibility
with these shared selections. No source override or DEB producer is introduced.
