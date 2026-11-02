# Management-framework runtime and debug TARs

Registers source revision [4036a01aa4648913ce44a0b4db52556a55cb2911](https://github.com/securely1g/sonic-mgmt-framework/tree/4036a01aa4648913ce44a0b4db52556a55cb2911) from [Framework PR #1](https://github.com/securely1g/sonic-mgmt-framework/pull/1).
The only source patch sets the immutable MODULE version.

The AMD64/Trixie consumer builds the owner's REST server, generated REST UI and
patched klish CLI, then composes its runtime TAR with management-common's
schema/data TAR as required by `docker-sonic-mgmt-framework`. Matching debug
symbols remain a separate TAR from the same native outputs. Its five tests
check complete payloads and symbols, actual installed REST TLS/CLI execution,
repeated model generation and supported generator configuration. It does not
claim a complete Docker or VS image.

The consuming root loads the owner's exported Go work file and patches, preserving
the deployed native Go library versions. It selects Go 1.25.9, Python 3.13 and
shared execution tools through the registry. No source archive override,
local source checkout or DEB generation is used by the consumer.

This Draft stack requires [management-common registration #165](https://github.com/securely1g/sonic-bazel-registry/pull/165),
[CLI tools/linker registration #168](https://github.com/securely1g/sonic-bazel-registry/pull/168)
and the Framework source PR. The temporary base combines the two reviewed
registration histories so validation uses one SONiC registry endpoint. Retarget
to main after those prerequisites land.
