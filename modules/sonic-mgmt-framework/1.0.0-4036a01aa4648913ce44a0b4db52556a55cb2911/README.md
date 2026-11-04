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

The initial shared graph at complete catalog `28bd77d92d8d28f100ca328489a49f3b025e1a65` passed all seven ordinary build outputs and all ten original test targets on native AMD64/Trixie. Independent verification checks every retained output/input hash, fetched module, nonempty test XML and successful build/test event. The installed REST binary reports Go 1.25.9 with glog 1.2.4, net 0.55, crypto 0.52, sys 0.45 and text 0.39. Runtime/debug TAR hashes are `029f87e5cbc5a147405bd72745ba8e3af166070ba231e615f6e96cb239f085fa` and `49af80b7afa83cad33a8bf1f0224c1819dc42352c8b57b0d59940434df07b161`. This is an ordinary-consumer result, separate from image acceptance.

The review base preserves every published infrastructure version, including
.26-51c, while this candidate selects the maintained .25-3ee source through
matching registry, source MODULE and ordinary-consumer declarations. Production
Framework source, runtime contracts and all seven outputs/ten tests are unchanged.
Earlier ordinary and image validation remains bound to its original catalogs.

This dependency refresh selects maintained infrastructure source 3ee15ec9 through
registry #218. Its numeric version is .25; published .26 entries remain intact.
Fresh module-graph checks must verify the selected version, followed by the
unchanged ordinary-consumer outputs and tests. This metadata/source-patch proof
does not establish native or image acceptance. Existing worker runs and earlier
receipts retain their exact preceding dependency inputs.
