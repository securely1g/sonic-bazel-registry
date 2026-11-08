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

Revision `0.1.3.sonic.3` keeps the source archives, public outputs, and presubmit
target list from `.sonic.2`. Its shared infrastructure requirement also includes
the linker-environment adapter described below. The foreign C++ rule enables
its standard `configure_xcompile` option, which supplies Autoconf's host/build
triplets when target and execution platforms differ. Native invocations retain
their normal configure behavior.

The source patch checks both vendored inputs on the build machine. Top-level
configure reads the gtest source, and proto configure reads
`p4/v1/p4runtime.proto`. Both keep their existing missing-submodule errors.
[Patch](overlay/bazel/cross-configure.patch)

`.sonic.2` and its consumer inputs remain unchanged. See [PATCHES.md](PATCHES.md)
for the source patch scope. PI's dependency graph has no new P4C dependency.

## Large linker environments

In [buildimage #133's full VS build](https://github.com/securely1g/sonic-buildimage/actions/runs/42405527456/job/128508038265),
PI's SDK received a 160,581-byte `LDFLAGS` value containing 573 `-L` library
search paths. That single environment value exceeded the runner's process
limit, so `/bin/sh` failed with `Argument list too long` before PI's configure
script could start.

| Input or action | Before | After |
| --- | --- | --- |
| Start PI configure with that library closure | The first shell cannot start with the large exported `LDFLAGS` value. | The shared `configure_linker_flags.sh` adapter is sourced first, saves the flags, and exports a short reference to `.sonic-linker-arguments`. |
| Compile and link through Autoconf and recursive Libtool | Configuration never reaches these commands. | The existing shared compiler adapter restores the ordered arguments and shortens absolute `-L` paths relative to each command's working directory. |

The adapter uses the already declared `foreign_runtime` Python interpreter.
PI declares its shared helper as build data; it does not copy BMv2's adapter or
add a dependency on BMv2. Compiler options, `CPPFLAGS`, library search order,
linker hardening flags, and the native/cross configure settings are preserved.

The shared adapter is implemented in
[build-infra #91](https://github.com/securely1g/sonic-build-infra/pull/91).
This recipe requires
`sonic-build-infra 0.0.28-65c32bdee82904de3edf1fa97325778bb574d5d8`, whose
[source includes the adapter](https://github.com/securely1g/sonic-build-infra/blob/b5a6094d703f6cf8132edc7ceb0326a464e3c5d1/tools/build_tools/configure_linker_flags.sh)
alongside the existing native-runtime and APT compatibility changes.

The shared `//tools/build_tools:libtool_test` covers the argument transport and
recursive working directories. PI's existing AMD64 and ARM64 consumer checks
remain required. Those component checks alone do not establish that the full VS
dependency closure builds; the downstream VS workflow must pass separately.

## APT lock input transport

PI's standalone ARM64 CI selected `rules_distroless 0.9.4.sonic.17` and
exhausted the existing 2 GiB Bazel heap while serializing module-extension
metadata into the lockfile, before the SDK build could start. The consumer's
selected graph and the lockfile serialization stack trace are retained in the
[failed CI run](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42434823648/job/128591369164).

This recipe and its standalone CI consumer both require
`rules_distroless 0.9.4.sonic.18`, which reuses
[registry #237's APT lock input transport fix](https://github.com/securely1g/sonic-bazel-registry/pull/237).
The fixed entry must be present in the registry alongside the build-infra
candidate. The shared transport avoids repeatedly embedding lock input contents
in generated repository attributes. This does not change PI's selected APT
packages, increase the CI heap, or remove any native or cross-build checks.

## Generated runtime package metadata

`//:runtime_packages.json` is a generated target. The existing Debian
`control` and `changelog` define package fields; `BUILD.bazel` maps package names
to the existing Bazel TARs. The shared metadata rule inspects those target
binaries and declared dependency packages, so version constraints come from
the built artifacts and Debian tools. There is no handwritten JSON metadata
file or new DEB producer.
