# Management-common source owner

Registers `sonic-mgmt-common@1.0.0-af147e78654ad423ea0a2af268dfd0b71092b38b` from
[the exact source revision](https://github.com/securely1g/sonic-mgmt-common/tree/af147e78654ad423ea0a2af268dfd0b71092b38b).
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

The source PR and OpenConfig linter registration must land before this Draft
registration becomes Ready:

- [management-common #1](https://github.com/securely1g/sonic-mgmt-common/pull/1)
- [registry #163](https://github.com/securely1g/sonic-bazel-registry/pull/163)
