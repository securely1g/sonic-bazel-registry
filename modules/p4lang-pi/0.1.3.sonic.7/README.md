# PI source producer for SONiC

This entry builds the exact `p4lang-pi 0.1.3-2` source package selected by the
legacy SONiC Make rules. Its expanded submodules come from the checksum-verified
original source archive, mirrored unchanged in the registry's
`p4-source-inputs-20261021` release. The release includes the descriptor and SHA-256
provenance receipt. No upstream BCR entry exists for PI under its known names.

The source's configure/Make build retains `--with-proto --with-cli`, the Debian
P4Info compatibility edit, and SONiC's omission of `google/__init__.py`. Native and cross
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

AMD64 builds and ARM64 cross builds compile both TARs and the SDK, compile/run a C++
SDK consumer, check runtime ELF architecture/SONAME links and debug build IDs,
load the installed tools with declared target libraries, round-trip P4Info text
through its binary protobuf form, and resolve a source line with GDB. ARM64
runtime validation executes the actual ARM64 binaries in the configured target
runtime. Both architectures must pass before merge.
This producer must land before consumers replace their temporary candidate pin.

The upstream Make build always receives `-g` and the shared linker build-ID
flags, disables the `strip_debug_symbols` linker feature, and uses `install`
without stripping. Runtime/debug splitting consumes installed SDK ELFs directly.
The package test verifies retained DWARF and matching build IDs.
The source-free `pi_CLI_dummy` launcher resolves `main` from `libpicli.so.0`;
validation checks that forwarding relationship and GDB source-line lookup in
the library's matching debug file. The compiled C++ SDK consumer runs against
the same installed runtime and declared target-library closure.

## Cross compilation

Revision `0.1.3.sonic.3` keeps the source archives, dependency versions, public
outputs, and presubmit target list from `.sonic.2`. The foreign C++ rule enables
its standard `configure_xcompile` option, which supplies Autoconf's host/build
triplets when target and execution platforms differ. Native invocations retain
their normal configure behavior.

The source patch checks both vendored inputs on the build machine. Top-level
configure reads the gtest source, and proto configure reads
`p4/v1/p4runtime.proto`. Both keep their existing missing-submodule errors.
[Patch](overlay/bazel/cross-configure.patch)

`.sonic.2` and its consumer inputs remain unchanged. See [PATCHES.md](PATCHES.md)
for the patch scope. This candidate is stacked on the separate P4C registration
PR only to support the runner migration's review order; PI's dependency graph
has no new P4C dependency.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
