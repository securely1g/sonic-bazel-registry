# Native Framework CLI

This version pins Framework source `07de59606b0b37a105544284405e86e1a27051bf`
and maintains the native CLI adaptation in this registry. No Framework source-repository changes are required by this entry.

The existing Infra `prepared_source` rule prepares the original patched klish
2.1.4 sources. Native `cc_library`, `cc_shared_library` and `cc_binary` targets
compile and link 99 C/C++ source files. Both AMD64 and ARM64 Linux/Trixie targets
use the configuration confirmed by controlled target-toolchain probes. Normal
builds invoke neither configure nor Make. Existing REST/model/CLI asset actions,
public runtime/debug TAR targets, installed paths, SONAMEs and archives remain.

The independent consumer selects this exact version and reads the Framework Go
workspace; the fetched module contributes its own `go.mod`. The presubmit retains
the published AMD64 seven build and ten test targets. Registry presubmit owns validation of the fetched module.

## ARM64 validation inputs

The selected published Infra .44 Framework SDK set has only AMD64 inputs. ARM64
compilation was validated with a separate .44 source copy whose SDK requests
were extended with the four same-version ARM64 development roots through the
existing `apt/lock.py update` and `check` entry points. This added 16 ARM64 package
records while preserving all 2,719 existing package records, sources, AMD64 SDK
inputs and other collections. The updated producer lock is validation-only; it
is not published by this Framework registry entry.

With that explicit producer override, build `//CLI:klish`, `//dist:runtime` and
`//dist:runtime.debug_symbols` for
`@sonic_build_infra//platforms:aarch64_trixie` with AMD64 execution tools. The
existing package contract accepts the target CPU (`x86_64` or `aarch64`), allowing
host-side inspection of all eight ELF/debug pairs without executing ARM64 code.
All five installed archives were separately checked for AArch64 object members.
AMD64 execution tests retain their existing platform constraints.
