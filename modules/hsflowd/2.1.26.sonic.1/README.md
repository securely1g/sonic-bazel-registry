# hsflowd 2.1.26.sonic.1

Source: `sflow/host-sflow` tag `v2.1.26-1`, commit
`41f10e6a2068ff15856e2bd1f1af2df1a506461b`. The SONiC package identity remains
`hsflowd 2.1.26-1`; `.sonic.1` identifies the registry build/patch adaptation.

This is the source producer for [buildimage issue #95](https://github.com/securely1g/sonic-buildimage/issues/95).
[sFlow image integration #132](https://github.com/securely1g/sonic-buildimage/issues/132)
separately consumes its runtime/debug outputs alongside SWSS, sflowtool and
libpsample. The hsflowd producer does not depend on either of those last two
packages: its selected PSAMPLE module uses the source owner's netlink code.

## Source contract

Both selected SONiC patches remain byte-for-byte unchanged: the Debian recipe
defines the `SONIC VPP` feature set and the VPP fix preserves SONiC counter
ownership for OS-index ports. Bazel does not run the Debian recipe or produce
a DEB. Maintained BUILD files sit beside the Linux, sFlow and bundled cJSON
sources; ordinary compiler actions cache each translation unit separately.

The build uses SONiC's declared native AMD64/Trixie GCC toolchain. It retains
the three source dialects: GNU99 for Linux, C99 for the owner's sFlow library,
and C89 for bundled cJSON. The legacy Linux Makefile defaults to Clang while
its bundled libraries default to GCC; this migration explicitly uses the
shared GCC toolchain, rather than depending on those ambient compilers.
Linux retains the selected `-g -gdwarf-4 -O2` settings, PIC, SONiC feature
defines, mount paths, module directory and exported main-program symbols.
The bundled libraries retain their own source settings.

The runtime consists of `/usr/sbin/hsflowd` plus JSON, DNS-SD, SONiC, PSAMPLE,
Docker, drop-monitor and VPP modules under `/etc/hsflowd/modules`. The SONiC
module consumes the shared locked Debian hiredis headers/library. Other
project code comes from the pinned source archive. Configuration, Debian init
script, DBus policy, license and versioned changelog are declared payloads.

Final modes follow the selected Debian recipe's normal `dh_fixperms` stage:
0755 for the daemon and init script, 0644 for modules and configuration.
Upstream `make install` alone initially uses 0700 for the daemon and 0755 for
modules; copying those intermediate modes would not preserve the final
package contract. The shared debug-splitting rule consumes the same linked
ELFs used by the runtime archive.

## Public targets

| Target | Output |
| --- | --- |
| `@hsflowd//:runtime` | Installed runtime TAR |
| `@hsflowd//:runtime.debug_symbols` | Matching Build-ID symbol TAR |
| `@hsflowd//:runtime_packages.json` | Source-owned installed package metadata |
| `@hsflowd//:hsflowd` | Unstripped daemon without build-tree search paths |
| `@hsflowd//:mod_sonic` and the other module names | Corresponding unstripped module |

Container composition, service policy and hardware/kernel sampling acceptance
remain in the consuming Docker integration. A successful source/TAR build is
not a claim of full VS or physical packet-sampling validation.

## Build and test

Add `bazel_dep(name = "hsflowd", version = "2.1.26.sonic.1")` to a SONiC
consumer using the shared native AMD64/Trixie toolchain. Before publication,
select the reviewed complete registry commit and BCR as described in the
[registry policy](../../../README.md#publishing-and-migrating-versions).

```sh
bazel build --platforms=@sonic_build_infra//platforms:x86_64_trixie \
  @hsflowd//:runtime @hsflowd//:runtime.debug_symbols \
  @hsflowd//:runtime_packages.json
bazel test --platforms=@sonic_build_infra//platforms:x86_64_trixie \
  @hsflowd//src/json:all @hsflowd//:package_test
```

Registry CI builds the daemon, all seven modules and the three TAR/metadata
outputs. It runs the 22 original cJSON test programs with their original
assertions, plus an installed-package test. That test checks paths, modes,
package dependencies, all eight ELF/Build-ID/debug-link pairs, and GDB source,
line and type information, including a missing-symbol negative check.

The installed test starts a declared private Redis instance, exercises the
SONiC module's database configuration and polling update, and sends JSON
metrics through the installed daemon to a local UDP collector. It decodes the
resulting sFlow datagrams and checks both metric values. Redis is test data;
it is not added to the hsflowd runtime TAR. The registry's pinned native test
container supplies GDB. These checks do not simulate a VPP dataplane, kernel
packet sampling or physical ASIC traffic.

## Routine maintenance

Add Linux daemon sources to `src/Linux/BUILD.bazel`, sFlow library sources to
`src/sflow/BUILD.bazel`, and bundled JSON sources or original test programs to
`src/json/BUILD.bazel`. Keep selected Linux flags and defines in
`bazel/settings.bzl`. A new installed module also needs its root BUILD target,
runtime mapping, debug-test symbol and `presubmit.json` selection; the package
test checks the exact installed payload and every native symbol pair.

Declare external dependencies in `MODULE.bazel` and the owning target. Do not
copy Make-built project packages into the runtime. After changing the module
declaration, run `ci/registry_ci.py sync-module --module hsflowd --version
2.1.26.sonic.1`; refresh the integrity of each changed overlay in `source.json`.
Use a new version for published build-input changes, following the registry
policy. CI checks entry integrity, the fetched module identity, all declared
outputs and the complete test selection.
