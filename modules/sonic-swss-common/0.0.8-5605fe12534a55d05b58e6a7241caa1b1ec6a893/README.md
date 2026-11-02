# Common Go binding and native libraries for gNMI

This single unreleased Common candidate selects owned snapshot
`5605fe12534a55d05b58e6a7241caa1b1ec6a893`, combining the unchanged source
commits from [Common #38](https://github.com/securely1g/sonic-swss-common/pull/38)
and [Common #39](https://github.com/securely1g/sonic-swss-common/pull/39).
Both retain [Common #37](https://github.com/securely1g/sonic-swss-common/pull/37)'s
declared runtime loader and Go XML self-execution fixes.

The native gNMI migration in [buildimage #110](https://github.com/securely1g/sonic-buildimage/issues/110)
imports `github.com/sonic-net/sonic-gnmi/swsscommon`. Common's owner target
`@sonic_swss_common//goext:swsscommon` accepts that spelling and its canonical
import while retaining one generated Go/C++ binding and public type identity.
Its runtime TAR also needs `libsonicdbcli.so.0`. The native `:libzmq_cc`
interface keeps ZMQ's payload and declared runtime closure without forwarding
unrelated development-library linker scripts as direct CLI link inputs.
That avoids looking for Trixie's libbsd file on an Ubuntu execution host.
Legacy Make behavior remains unchanged.

The native AMD64/ARM64 registry consumer retains all 13 build targets and
17 existing tests, including the loader, hiredis, alias and runtime/debug
package checks. It adds the declared-loader CLI ABI test, for 18 tests total.
The Go consumer uses 1.25.9; source CI separately covers both YANG modes.
Common #39's additional Ubuntu job proves the CLI/package checks pass while
the target-distro libbsd file is absent. No DEB producer is selected.
Full gNMI service and installed-image coverage belongs to the separate owner
and image migrations.

The source repository owns both implementation features. The sole registry
patch changes the module version. Published Common versions remain unchanged;
this replaces the preceding `.8` draft in the same stack rather than adding a
second unreleased candidate. Source #37/#38/#39, registry #161's native-loader
registration, and registry #146's native APT interface remain unlanded.
The owned registry base combines #161 and #146 without rewriting either
contributor branch. Keep the registration Draft until its required source and
registry contents land, then recheck immutable pins and validation.
