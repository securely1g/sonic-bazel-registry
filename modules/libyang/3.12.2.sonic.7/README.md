# libyang 3.12.2.sonic.7

Cross-build the same seven build targets and five test targets as .6 for
AArch64 on the AMD64 Trixie runner. The original Tcl/Expect suite repeatedly
spawns yanglint and yangre with a five-second startup deadline. Prepare their
declared target dependencies before entering the suite and run the ARM binaries
for every invocation. The upstream assertions and timeouts still apply.

The upstream driver waits for the Tcl process to exit before closing the
controlling PTY. Tcl child interpreters use the same declared tclsh launcher
as their parent. These changes and the build-time runtime preparation come
from [the .7 candidate in PR #282](https://github.com/securely1g/sonic-bazel-registry/pull/282).
The consumer pins the published build-infra .28-9965823, Distroless .18 and
tar.bzl .2. The shared Trixie and Bookworm APT lock provides the dependencies.

### Prepared CLI test runtimes

The `test_yanglint` and `test_yangre` wrappers prepare their runtime closure once as declared native build actions. They call the selected infra runtime validator with the explicit target CPU, original target binary/runfiles and original payloads. The existing instrumentation boundary captures the already-validated loader, libraries and debug files into a declared runtime tree; it never executes a target during preparation. Target ELF, payload architecture, SONAME, debug-link and transitive RPATH checks still run. A relocatable manifest records the validator and target hashes plus every captured runtime file.

Each test invocation still executes the genuine target loader and original binary. Its original binary path/runfiles, working directory, arguments and caller environment are preserved, with the same three loader environment variables removed. A small statically linked execution-platform path resolver preserves the original binary symlink/RPATH semantics without starting Python or consuming its startup environment. This removes repeated archive/ELF preparation from the original five-second interactive startup deadline. Other runtime wrappers and arbitrary Python tests are unchanged. The full seven-build/five-test native and cross contracts remain the acceptance gate.

`tests/prepared_runtime_test.py` exercises capture architecture/command guards and a clearly labelled launcher surrogate for cwd/argument/environment preservation; it does not substitute for real target execution.
