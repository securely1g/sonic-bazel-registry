# libyang 3.12.2.sonic.7

This candidate keeps the same upstream 3.12.2 source, SONiC patch, native C
builds and installed-runtime/package checks as `.sonic.6`. All seven build labels
and five test labels remain unchanged on AMD64 and ARM64. Published entries stay
unchanged.

It selects `sonic-build-infra@0.0.28-6f48ad4e60916f004d6498d9cc1d228cf0af7134`
([source PR #88](https://github.com/securely1g/sonic-build-infra/pull/88)) so
`native_runtime_binary` prepares runtime files with a declared execution-platform
Python while preserving target-CPU validation and real target binary execution.
The direct `tar.bzl` request is aligned to `0.10.5.sonic.2`, already required by
that infra source, so the declared consumer pin matches Bazel's selected version.

The interactive upstream-test driver now waits for Tcl's actual exit before
closing the controlling PTY. Closing at PTY EOF could otherwise send SIGHUP
before Tcl completed. Test cases, assertions, exit-code checks and original
five-second Expect timeouts are unchanged.

A standalone regression exercises both the unchanged `.6` driver and this driver
using real controlling terminals: successful exit, nonzero exit, failed Tcl
summary, and a noninteractive control. Run it from the registry root with an
unused output directory:

```sh
python3 modules/libyang/3.12.2.sonic.7/tests/pty_wait_test.py --output /tmp/libyang-pty-regression
```

The earlier bounded real ARM replay passed the original `add_basic` assertions
with native preparation and the corrected PTY order. Full seven-build/five-test
acceptance and before/after selected-graph evidence are still required for this
draft; the focused replay alone is not full module acceptance.
