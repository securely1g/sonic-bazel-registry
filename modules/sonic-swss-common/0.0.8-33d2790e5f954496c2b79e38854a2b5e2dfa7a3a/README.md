# Common Go binding, native libraries and Lua scripts for gNMI

This single unreleased Common candidate selects owned snapshot
`33d2790e5f954496c2b79e38854a2b5e2dfa7a3a`, combining the unchanged source
commits from [Common #38](https://github.com/securely1g/sonic-swss-common/pull/38),
[Common #39](https://github.com/securely1g/sonic-swss-common/pull/39), and
[Common #40](https://github.com/securely1g/sonic-swss-common/pull/40).
They retain [Common #37](https://github.com/securely1g/sonic-swss-common/pull/37)'s
declared runtime loader and Go XML self-execution fixes.

The native gNMI migration in [buildimage #110](https://github.com/securely1g/sonic-buildimage/issues/110)
imports `github.com/sonic-net/sonic-gnmi/swsscommon`. Common's owner target
`@sonic_swss_common//goext:swsscommon` accepts that spelling and its canonical
import while retaining one generated Go/C++ binding and public type identity.
Its runtime TAR also needs `libsonicdbcli.so.0`. The native `:libzmq_cc`
interface keeps ZMQ's payload and declared runtime closure without forwarding
unrelated development-library linker scripts as direct CLI link inputs.
That avoids looking for Trixie's libbsd file on an Ubuntu execution host.
The real gNMI `TestZmqReconnect` also reads the owner Lua script through
`SWSS_COMMON_LUA_DIR` in a private extracted runtime. Unset/empty variables
preserve `/usr/share/swss`; basenames and canonical containment reject traversal
and symlink escape. No host installation is needed.
Legacy Make behavior remains unchanged.

The native AMD64/ARM64 registry consumer retains all 13 build targets and
18 existing tests, including the loader, hiredis, alias, CLI ABI and runtime/debug
package checks. It adds the declared-runtime Lua-path test, for 19 tests total.
The Go consumer uses 1.25.9; source CI separately covers both YANG modes.
Common #40 passes both native YANG modes and CodeQL; the real downstream
ZMQ reconnect case passes three serial race-enabled repetitions.
Common #39's additional Ubuntu job proves the CLI/package checks pass while
the target-distro libbsd file is absent. No DEB producer is selected.
Full gNMI service and installed-image coverage belongs to the separate owner
and image migrations.

The source repository owns all three implementation features. The sole registry
patch changes the module version. Published Common versions remain unchanged;
this replaces the preceding `.8` draft in the same stack rather than adding a
second unreleased candidate. Source #37/#38/#39/#40, registry #161's native-loader
registration, and registry #146's native APT interface remain unlanded.
The owned registry base combines #161 and #146 without rewriting either
contributor branch. Keep the registration Draft until its required source and
registry contents land, then recheck immutable pins and validation.

## Shared netlink ownership for Linkmgrd

[Common #41](https://github.com/securely1g/sonic-swss-common/pull/41) declares
libnl's three native shared providers and runtime package metadata in Common.
Linkmgrd's `//:linkmgrd` needs Common and libnl base/route together. Previously
Bazel rejected their duplicate ownership because Common embedded libnl static
objects. The owner change uses the original shared providers instead. It also
preserves each owner's runtime TAR; consumers install the libnl TARs alongside
Common. No DEB producer is selected.

The original 13 build targets and 19 tests remain. Two additional tests link
and execute the Common/base/route/netfilter APIs together and check Common's
ELF dependencies and absence of embedded libnl symbols (21 tests total).
Both native architectures are retained; the consumer explicitly requires
`libnl3@3.7.0.sonic.7` from [registry #181](https://github.com/securely1g/sonic-bazel-registry/pull/181).
It retains #148's native support and gives the original shared outputs their
SONAME filenames, so Common's unwrapped C++ and Rust tests can load them from
Bazel runfiles. This source replaces the preceding
unreleased .8 candidate, preserving all existing feature commits and the
version-only registry patch. Registry and installed consumer acceptance are
pending; no complete Linkmgrd/OCI result is claimed.

The native libnl interface also loads the shared test/runtime helpers from
[registry #179](https://github.com/securely1g/sonic-bazel-registry/pull/179).
The owner and external consumer both declare that minimum infrastructure
version; merely changing the registry endpoint cannot raise a module minimum.
