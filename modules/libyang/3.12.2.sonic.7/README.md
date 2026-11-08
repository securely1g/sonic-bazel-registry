# libyang 3.12.2.sonic.7

This candidate keeps the same upstream 3.12.2 source, SONiC patch, native C
builds and installed-runtime/package checks as `.sonic.6`. All seven build labels
and five test labels remain unchanged on AMD64 and ARM64. Published entries stay
unchanged.

It selects `sonic-build-infra@0.0.28-b55ad3322094b87a682b6ef22ec500696a183b6d`
([source PR #88](https://github.com/securely1g/sonic-build-infra/pull/88)) so
`native_runtime_binary` prepares runtime files with a declared execution-platform
Python while preserving target-CPU validation and real target binary execution.
The direct `tar.bzl` request is aligned to `0.10.5.sonic.2`, already required by
that infra source, so the declared consumer pin matches Bazel's selected version.

It also selects `rules_distroless@0.9.4.sonic.18` explicitly in the module and
CI consumer. Its APT extension writes each transformed package catalog once and
passes file labels to dependency groups, preserving the reviewed package sets
while avoiding repeated catalog serialization in `MODULE.bazel.lock`. The normal
2 GiB Java heap and every build/test target remain unchanged.

The Trixie dependency alias consumes infra's existing reviewed `libyang_deps`
collection. All eight directly required package identities and SHA256 values
match the original `.6` graph on AMD64 and ARM64. The source lock has one
transitive cleanup on AMD64: it retains security `linux-libc-dev` 6.12.96-1 and
omits the redundant older 6.12.86-1 record. No upstream archive checksum or
source snapshot is edited. The Bookworm namespace now imports the same shared
lock through the selected infra source.
This entry retains its existing exact package requests and two source
declarations; they agree with the locked Bookworm records. The source includes
[infra #90](https://github.com/securely1g/sonic-build-infra/pull/90) alongside
#88's runtime preparation, so existing image and historical library consumers
can select that one reviewed package graph. The source also preserves #88's
fix for closed standard file descriptors and the shared configure/Make linker adapter
from [infra #91](https://github.com/securely1g/sonic-build-infra/pull/91).
Libyang continues to use its existing native C build targets.

The interactive upstream-test driver now waits for Tcl's actual exit before
closing the controlling PTY. Closing at PTY EOF could otherwise send SIGHUP
before Tcl completed. Test cases, assertions, exit-code checks and original
five-second Expect timeouts are unchanged.

Tcltest's child interpreter is explicitly bound to the same declared public
`tclsh` launcher as the parent. Its default raw interpreter path bypassed the
private loader and failed to find `libtcl8.6.so` in per-file subprocesses. A small
bootstrap preserves the original suite path and arguments before sourcing each
unchanged `all.tcl`; multi-process execution and strict nonzero test counts stay
enabled. No loader environment is injected into target programs.

A standalone regression exercises both the unchanged `.6` driver and this driver
using real controlling terminals: successful exit, nonzero exit, failed Tcl
summary, and a noninteractive control. Run it from the registry root with an
unused output directory:

```sh
python3 modules/libyang/3.12.2.sonic.7/tests/pty_wait_test.py --output /tmp/libyang-pty-regression
```

The child-interpreter regression uses real Tcltest subprocesses, checks each
declared launcher traversal and original arguments, reproduces raw-interpreter
bypass, and rejects a missing declared interpreter. It requires an explicit
interpreter, for example:

```sh
python3 modules/libyang/3.12.2.sonic.7/tests/tcl_interpreter_test.py --tclsh /absolute/path/to/declared/tclsh
```

The earlier bounded real ARM replay passed the original `add_basic` assertions
with native preparation and the corrected PTY order. Full seven-build/five-test
acceptance and before/after selected-graph evidence are still required for this
draft; the focused replay alone is not full module acceptance.

### Prepared CLI test runtimes

The `test_yanglint` and `test_yangre` wrappers prepare their runtime closure once as declared native build actions. They call the selected infra runtime validator with the explicit target CPU, original target binary/runfiles and original payloads. The existing instrumentation boundary captures the already-validated loader, libraries and debug files into a declared runtime tree; it never executes a target during preparation. Target ELF, payload architecture, SONAME, debug-link and transitive RPATH checks still run. A relocatable manifest records the validator and target hashes plus every captured runtime file.

Each test invocation still executes the genuine target loader and original binary. Its original binary path/runfiles, working directory, arguments and caller environment are preserved, with the same three loader environment variables removed. A small statically linked execution-platform path resolver preserves the original binary symlink/RPATH semantics without starting Python or consuming its startup environment. This removes repeated archive/ELF preparation from the original five-second interactive startup deadline. Other runtime wrappers and arbitrary Python tests are unchanged. The full seven-build/five-test native and cross contracts remain the acceptance gate.

`tests/prepared_runtime_test.py` exercises capture architecture/command guards and a clearly labelled launcher surrogate for cwd/argument/environment preservation; it does not substitute for real target execution.
