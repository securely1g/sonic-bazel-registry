# Static C launchers with GCC and Clang

This entry pins [shared source `76d4fbc28658adfd88871d991ca7b81c5c511933`](https://github.com/securely1g/sonic-build-infra/commit/76d4fbc28658adfd88871d991ca7b81c5c511933) and applies only the registry version suffix. It incorporates the reviewed [infra #60](https://github.com/securely1g/sonic-build-infra/pull/60) correction above the existing combined source, retaining [infra #56](https://github.com/securely1g/sonic-build-infra/pull/56)'s compiler argument and Libtool fixes and the OCI metadata helpers.

The C-only tool bootstrap disables LLVM's dynamic C++ standard-library feature on this target. Its declared C sysroot and compiler resources remain in use. Native GCC and Clang coverage checks the static ELF, wrapper execution, preserved arguments and exit status, alongside the normal C++ ABI probes. Autoconf, Automake and Libtool remain pinned Debian tool packages.

Fetched-module CI runs the existing 28 build targets and 15 uncached tests on native AMD64 and ARM64 with explicit target and execution platforms. Coverage includes Make/configure/Libtool execution, runtime linking and runtime/debug TARs. The selected targets produce no DEBs. Both native jobs are required before readiness.

Direct merge gates: [registry #118](https://github.com/securely1g/sonic-bazel-registry/pull/118), infra #56 and infra #60. The temporary base supplies the reviewed shared CI and directory-artifact support. Retarget to main after those prerequisites land and revalidate. This is a new immutable version; existing `.21` entries remain available.
