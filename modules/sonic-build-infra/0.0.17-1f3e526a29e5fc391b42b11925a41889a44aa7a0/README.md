# Repository sysroot with declared source-build tools

This candidate registers `sonic-build-infra` source
`1f3e526a29e5fc391b42b11925a41889a44aa7a0`, an explicit temporary composition of:

- [Configure tools #36](https://github.com/securely1g/sonic-build-infra/pull/36), source `21dde7f92819f605382604d3f49213e83a2bd567`.
- [Declared GCC paths #37](https://github.com/securely1g/sonic-build-infra/pull/37), source `8faa536a1294c53274b67659d501075da252d1f6`.
- [Repository sysroot #40](https://github.com/securely1g/sonic-build-infra/pull/40), source `b556ca8480419f18fc4d25e72872fd749bb1e133`.
- [Kerberos generators #41](https://github.com/securely1g/sonic-build-infra/pull/41), source `6db0e2e40e41a2700bd1fc0f54f8762ebf3dba00`.

The first two features come from exact integration foundation
`3d896318a3627c4ef63010e8b9e4488fa1977161`. The module base advances to `0.0.17`
for the repository-sysroot API. The only registry patch aligns that module version
with the full source commit. Published entries and registry #60 remain unchanged.

The initial consumer is the source-built `sonic-fips //symcrypt:core` target,
whose native build selects Clang. `sysroots.debian` supplies the existing pinned
Trixie headers and libraries to the maintained LLVM toolchain's repository-sysroot
API, including complete GCC development-library links. Kerberos consumers also receive the declared compile_et and mk_cmds generators. Compiler registration
remains the consumer's responsibility.

Source #40's external LLVM19.1.7 consumer passes on native AMD64 and ARM64,
checking compiler/header paths, archive provenance, relative and complete links,
and execution through the declared loader/libraries. This registry's native
consumer checks the selected archive/module and the existing declared GNU tools,
configure build, compiler paths, library linking and the Kerberos generators. The source-owned LLVM check
is separate evidence; it is not claimed to run in the registry target suite.

This is an unlanded integration snapshot. Keep this registration and consumers
Draft until all source prerequisites are merged and the pins are refreshed.
