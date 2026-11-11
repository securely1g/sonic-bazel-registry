# PI source producer for SONiC

This recipe builds the exact `p4lang-pi 0.1.3-2` source package selected by SONiC.
The checksum-verified original archive includes its expanded submodules and is
mirrored unchanged in the registry's `p4-source-inputs-20261021` release with
its descriptor and provenance receipt. It reuses the existing pinned source
importer, SONiC toolchain, generators, target libraries and SDK/TAR helpers.

## Outputs

- `:sdk` provides installed headers, libraries and `CcInfo`, including generated
  P4Runtime/gNMI headers for BMv2 and DASH.
- `:runtime` contains stripped PI libraries, the three runtime programs
  `pi_CLI_dummy`, `pi_gen_native_json` and `pi_convert_p4info`, generated Python
  bindings under `/usr/lib/python3/dist-packages`, and license notices.
- `:runtime.debug_symbols` provides matching build-ID-addressed DWARF symbols.
- `:native_core` adds first-class Bazel core libraries from the pinned upstream
  BUILD source lists. Native versions of `pi_gen_native_json` and
  `pi_gen_fe_defines` provide a comparison with the installed SDK generators.

The SDK retains all twelve installed libraries, development headers, the FE
header generator and its Python layout. The FE executable is explicitly
exposed as an SDK data output. Runtime TARs exclude static archives, headers,
libtool archives, bytecode and Debian packages.

`//:runtime_packages.json` derives package fields from the existing Debian
`control` and `changelog`, maps them to the Bazel TARs, and inspects their binaries
and declared dependency packages. This recipe does not produce DEBs.

## Native dependencies and compatibility

The native core directly uses the public Bazel Central Registry targets
`@cjson//:cjson` (`1.7.19-0.20240923110858-12c4bf1986c2.bcr.4`) and
`@uthash//:uthash` (`2.3.0`). cJSON exports `cJSON.h` and links libm; uthash
exports `uthash.h`. There is no private dependency wrapper. The C++ frontend
in this slice does not require fmt.

Only `native_pip4info` defines `PI_NATIVE_PUBLIC_CJSON`. Its owned-source
conditional selects the public header and `cJSON_free` for serialized buffers,
using the public allocation/free-hook pairing. The configure/Make SDK path
retains its bundled header and `cJSON_Delete_char` call, which delegates to
the bundled free hook.

The SDK configuration and installed layout are preserved, but its source inputs
change. Added conditional lines can change DWARF line tables, build action keys
and output bytes even when the legacy code path has equivalent behavior.
Byte-identical rebuilt SDK outputs and automatic downstream acceptance are not
claimed. Complete native conversion of the shared libraries, protocol/Python
outputs, installed ABI including `libpigrpcserver`, and real BMv2 consumers
remains pending; the additive core does not establish that acceptance.

## SDK build configuration

The existing configure/Make build retains `--with-proto --with-cli`, the Debian
P4Info compatibility edit and SONiC's omission of `google/__init__.py`. Declared
Autotools, Libtool, Python, protoc and gRPC plugins use the shared SONiC GCC/sysroot
and pinned Trixie target libraries. Cross configuration supplies host/build
triplets and preserves the missing-submodule checks.

Configuration uses logical prefix `/usr`; `DESTDIR` and `install_prefix = "usr"`
keep staging separate from the flat `bin`, `lib`, `include` and `python` SDK.
`set_file_prefix_map = True` normalizes execution-root paths. The Make build
receives `-g` and shared build-ID flags, disables linker debug stripping, and
installs without stripping. Runtime/debug splitting consumes those SDK ELFs.

`sonic-build-infra 0.0.28-9965823498ab54816de5addb6084638470dd04d7` supplies the
existing linker-argument adapter and declared runtime interpreter, preserving
argument order and hardening flags without oversized exported `LDFLAGS`.
`rules_distroless 0.9.4.sonic.18` supplies the existing APT lock-input transport.
See [PATCHES.md](PATCHES.md) for the source adaptation rationale.

## Configured validation

AMD64 and ARM64 retain the SDK, runtime and debug-TAR builds and their existing
tests: a C++ SDK consumer, ELF architecture and SONAME links, matching build IDs,
installed tools with their target-library closure, P4Info protobuf round trips,
and GDB source-line lookup. The dummy CLI's forwarding to `libpicli.so.0` remains
checked. ARM64 validation executes the target binaries; inherited global ARM
compatibility checks also remain selected.

Only AMD64 adds the native core and generator targets. `:native_generators_test`
compares native and installed generators on the original action-profile and
valid-match fixtures, checks JSON/header equality and argument behavior, and
requires ordinary error exits for missing, malformed and late-truncated JSON.
Signals and allocator aborts are failures. Successful generation exercises
configuration destruction and serialized-buffer deallocation; these checks do
not prove leak freedom or the complete native SDK/ABI conversion. Per-C++ action
query evidence is a separate validation requirement.
