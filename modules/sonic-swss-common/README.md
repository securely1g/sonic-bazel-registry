### sonic-swss-common 0.0.0-99572f5a34e7f408dee49eaf2a3ba60c5d443fb6

This release fetches the merged Common source at
[`99572f5`](https://github.com/securely1g/sonic-swss-common/commit/99572f5a34e7f408dee49eaf2a3ba60c5d443fb6).
Common owns its Bazel build and migration history. The registry carries only a
patch to the module version, matching the source commit named by the release.

This replaces the draft `0.0.0-10d14ae58ae73899a52a2447d1e791a2b7bd1a34` entry,
which applied the entire Bazel migration to an older source archive. That draft
entry has been removed from the current index. Its already-published immutable
registry snapshots (including `ab3d2af909a4791bdc53d3aa48005c36cb7d528a` and
`3131031ad639e33a6a99599b954863f9e9f62532`) retain exactly their original contents
for historical consumers. SWSS advances both its Common version and registry
pin together; there is no in-place change to the old module's source or hashes.

#### Registry CI

The version's `presubmit.json` selects the source repository's supported no-YANG
configuration on native AMD64 and ARM64 Debian Trixie. It builds the C++ library
and tool, Python and Go bindings, runtime packages, and matching detached debug
symbols through explicit required targets. The seven explicit source-owned tests
include the dynamic C API runtime test and the package layout and debug-symbol
checks.

The manifest adds no test-only dependencies to the published module. Registry CI
uses a separate `registry_ci_consumer` root; ordinary standalone and dependent
builds continue to use the source module's declarations and configuration.
