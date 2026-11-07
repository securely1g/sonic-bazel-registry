# Management-common source owner

Registers `sonic-mgmt-common@1.0.0-f5361ba8b88cde7ec59bdb4652a986c68d66da64` from
[the exact source revision](https://github.com/securely1g/sonic-mgmt-common/tree/f5361ba8b88cde7ec59bdb4652a986c68d66da64).
The only registry patch gives its MODULE the immutable source version.

The native AMD64/Trixie consumer compiles against the owner's public CVL,
translib and generated Go bindings, then builds and checks its runtime and
code-generation TARs. The actual generator runs 20 times to verify byte identity.
Go1.25.9/Python3.13 and the owner's exported dependency patches are selected by
the consuming root, on a single shared Go dependency graph. The small Go
consumer and root configuration follow the source owner's checked fixture;
implementation sources and schema generators stay with their owner.

Management-framework and gNMI consume these interfaces for their server builds
and install the runtime TAR in their images. Docker/VS assembly is separate.
No Debian package is generated. External locked distribution packages remain
allowed imported inputs.

The selected source is the maintained merge of
[management-common #1](https://github.com/securely1g/sonic-mgmt-common/pull/1).
Its source tree exactly matches the tested PR head. Compared with the earlier
`af147e7` candidate, only the source CI workflow and README changed; the producer,
public interfaces and both TAR outputs are unchanged. The OpenConfig linter
prerequisite [registry #163](https://github.com/securely1g/sonic-bazel-registry/pull/163)
is also merged. This registration targets maintained registry main.

The owner's recorded follow-ups for shared generator-patch ownership and
resolved-graph/working-tree checks remain separate from this registration.
