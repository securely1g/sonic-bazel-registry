# SONiC psample runtime and SDK

Build the exact Mellanox/libpsample revision selected by SONiC's `src/sflow/psample/Makefile`:
`e48fad2402500a2aeb73961729aad06f793ff46e`. There is no upstream Bazel module or test suite at this revision. The overlay runs the original CMake project through `rules_foreign_cc`; the two library sources, CLI, Debug build setting, and ABI are retained.

The real consumer is SONiC's `docker-sflow`: `rules/docker-sflow.mk` includes `PSAMPLE` and copies `/usr/bin/psample` into the base image. [Producer issue #97](https://github.com/securely1g/sonic-buildimage/issues/97) tracks this interface; [Docker issue #132](https://github.com/securely1g/sonic-buildimage/issues/132) tracks its OCI integration. No Docker consumer selects this module yet.

| Input or action | Existing Make path | This module |
| --- | --- | --- |
| Selected source `e48fad2` | Clone libpsample and run SONiC's Debian recipe | Fetch the same full revision and run its CMake build with the declared compiler and libmnl |
| Runtime psample package | `psample_1.1-1_amd64.deb` | `@libpsample//:runtime` contains the CLI, shared library, SONAME symlinks, compressed manual and notices |
| Debugging | `psample-dbgsym` | `@libpsample//:runtime.debug_symbols` matches the same two installed ELFs |
| Native consumer | Headers removed from the runtime package by Debian rules | `@libpsample//:libpsample` exports the upstream installed header and shared-library CcInfo separately |

## Version and dependency contract

`1.1.0.sonic.1` represents SONiC's package version `1.1-1`; it does not change the library ABI. Upstream CMake calls this library `1.0`, creates `libpsample.so.1.0`, and sets SONAME `libpsample.so.1`. Those names remain unchanged. The metadata target reads the original SONiC control/changelog copied from buildimage `73f6eba5cd26e1359a7026569402439951723df0`; it produces JSON, never a DEB.

The library depends on **libmnl**, not libnl3. The existing shared Debian snapshot supplies its declared development and runtime inputs. `@psample_deps//libmnl0:data` remains an external distro runtime input. Source/package outputs are independent of SWSS compilation and sFlow OCI assembly. The normal registry endpoint is maintained SONiC `main` plus Bazel Central Registry; draft validation explicitly substitutes this PR's one catalog.

Runtime paths are root-owned `/usr/bin/psample`, `/usr/lib/x86_64-linux-gnu/libpsample.so{,.1,.1.0}`, `/usr/share/man/man8/psample.8.gz`, and `/usr/share/doc/psample/copyright`. No headers enter the runtime TAR. Existing upstream license notices are retained verbatim; source comments remain the reference because the selected repository has no COPYING file. The compressed manual uses upstream `rules_gzip`, the existing pinned pigz execution tool, and `--no-name`.

## Validation and maintenance

Native AMD64/Trixie is the supported scope. The installed-package test checks paths, ownership, modes, symlinks, gzip metadata, SONAME/NEEDED entries, absence of build RPATHs, build IDs, debuglink CRCs, and GDB source/types with a negative control. A small consumer links the exported SDK, is copied away from Bazel library symlinks, and runs against the installed library.

The installed CLI receives sample and group-update netlink messages through a test-only replacement of the kernel transport functions. The actual installed library performs attribute parsing and callbacks; the actual CLI formats the sampled payload and notifications. Tests cover sample/config filtering, group listing, and a failed family-open operation. This is a declared protocol fixture, not proof of live kernel or ASIC packet sampling; the Docker integration retains that acceptance boundary. The upstream revision has no original unit-test target to silently omit.

Preserve existing source behavior when maintaining the overlay. The selected header declares `psample_get_log_level`, while the selected implementation exports `get_log_level`; this pre-existing upstream mismatch is not renamed by the migration. Do not claim that fixture tests prove all kernel transport behavior or malformed-message handling.

To update the source, first verify SONiC's Make selection, original CMake install outputs and source notices. Update the source checksum/overlays together, run the installed test, and verify an ordinary registry consumer, cached no-op, representative source edit, and restored output hashes. Keep the original Make/Debian path intact and do not generate DEBs with Bazel.
