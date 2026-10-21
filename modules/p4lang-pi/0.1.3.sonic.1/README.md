# PI source producer for SONiC

This entry builds the exact `p4lang-pi 0.1.3-2` source package selected by the
legacy SONiC Make rules. Its expanded submodules come from the checksum-verified
original source archive, mirrored unchanged in the registry's
`p4-source-inputs-20261021` release. The release includes the descriptor and SHA-256
provenance receipt. No upstream BCR entry exists for PI under its known names.

The source's configure/Make build retains `--with-proto --with-cli`, the Debian
P4Info compatibility edit, and SONiC's omission of `google/__init__.py`. Native
source builds use the shared SONiC GCC/sysroot and declared Autotools, Libtool,
Python, protoc and gRPC plugins. Target libraries come from the shared pinned
Trixie package resolver. These are execution/target inputs, not newly built DEBs.

## Public outputs

- `:sdk`: complete installed headers, libraries and `CcInfo`, including generated
  P4Runtime/gNMI headers for BMv2 and DASH.
- `:runtime`: stripped PI libraries and command-line tools, generated Python
  bindings under `/usr/lib/python3/dist-packages`, and license notices.
- `:runtime.debug_symbols`: matching build-ID-addressed DWARF symbols.

The SDK retains development files; runtime TARs do not include static archives,
headers, libtool archives, bytecode or Debian packages. Legacy Make is unchanged.

## Validation

Native AMD64 and ARM64 registry CI build both TARs and the SDK, compile/run a C++
SDK consumer, check runtime ELF architecture/SONAME links and debug build IDs,
load the installed tools with declared target libraries, round-trip P4Info text through its binary protobuf form, and resolve a source line with GDB. The native runs must pass before merge.
This producer must land before consumers replace their temporary candidate pin.

The upstream Make build always receives `-g` and the shared linker build-ID
flags, disables the `strip_debug_symbols` linker feature, and uses `install`
without stripping. Runtime/debug splitting consumes installed SDK ELFs directly.
The package test verifies retained DWARF and matching build IDs.
The source-free `pi_CLI_dummy` launcher resolves `main` from `libpicli.so.0`;
validation checks that forwarding relationship and GDB source-line lookup in
the library's matching debug file. The compiled C++ SDK consumer runs against
the same installed runtime and declared target-library closure.

## Dependencies and merge gates

Direct prerequisites are registry [#87](https://github.com/securely1g/sonic-bazel-registry/pull/87)
for shared build tools/compiler support and
[#91](https://github.com/securely1g/sonic-bazel-registry/pull/91) for complete target
headers. Their implementation comes from build-infra
[#53](https://github.com/securely1g/sonic-build-infra/pull/53) and
[#54](https://github.com/securely1g/sonic-build-infra/pull/54), and registry #91
includes the parser predecessor [#90](https://github.com/securely1g/sonic-bazel-registry/pull/90).

The temporary `codex/p4-pi-prerequisites` base combines those candidates in one
registry snapshot for native validation. Land the prerequisites, retarget this
producer to `main`, use merged source pins and rerun AMD64/ARM64 checks before
marking it ready to merge. BMv2 and DASH consumers must wait for this producer.
