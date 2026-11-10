# SONiC psample runtime and SDK

Build the exact Mellanox/libpsample revision selected by SONiC's `src/sflow/psample/Makefile`:
`e48fad2402500a2aeb73961729aad06f793ff46e`. There is no upstream Bazel module or test suite at this revision, and the Bazel Central Registry has no libpsample module (checked 2026-11-10). This revision replaces the earlier `rules_foreign_cc` CMake wrapper from `1.1.0.sonic.1` with native `rules_cc` targets (`cc_library`, `cc_shared_library`, `shared_library_cc_info`, and `cc_binary`) while preserving the two library sources, CLI, SONAME, and ABI.

The real consumer is SONiC's `docker-sflow`: `rules/docker-sflow.mk` includes `PSAMPLE` and copies `/usr/bin/psample` into the base image. [Producer issue #97](https://github.com/securely1g/sonic-buildimage/issues/97) tracks this interface; [Docker issue #132](https://github.com/securely1g/sonic-buildimage/issues/132) tracks its OCI integration.

| Input or action | Before (`1.1.0.sonic.1`) | After (`1.1.0.sonic.2`) |
| --- | --- | --- |
| Selected source `e48fad2` | Run the upstream CMake project through `rules_foreign_cc` | Compile `src/mnlg.c`, `src/psample.c` and `psample_tool/psample.c` directly with native `rules_cc` and locked `libmnl` |
| Runtime psample package | `@libpsample//:runtime` (AMD64 only) | `@libpsample//:runtime` for AMD64 and ARM64 (`libpsample.so.1.0`, SONAME symlinks, `/usr/bin/psample`, compressed manual and notices) |
| Debugging | `@libpsample//:runtime.debug_symbols` | Unchanged (`@libpsample//:runtime.debug_symbols` split from the same two linked ELFs) |
| Native consumer | `@libpsample//:libpsample` from foreign CMake output | `@libpsample//:libpsample` via `cc_shared_library` + `shared_library_cc_info` + `strip_include_prefix = "include"` |

## Version and dependency contract

`1.1.0.sonic.2` represents SONiC's package version `1.1-1`; it does not change the library ABI. Upstream `CMakeLists.txt` compiles `src/psample.c` and `src/mnlg.c` into `libpsample.so.1.0` with SONAME `libpsample.so.1`, and links `psample_tool/psample.c` dynamically against `libpsample.so.1`. Those names and linkage remain unchanged. The metadata target reads the original SONiC control/changelog copied from buildimage `73f6eba5cd26e1359a7026569402439951723df0`; it produces JSON, never a DEB.

The library depends on **libmnl**, not libnl3. The existing shared Debian snapshot supplies its declared development and runtime inputs. `@psample_deps//libmnl0:data` remains an external distro runtime input.

Runtime paths are root-owned `/usr/bin/psample`, `/usr/lib/{x86_64,aarch64}-linux-gnu/libpsample.so{,.1,.1.0}`, `/usr/share/man/man8/psample.8.gz`, and `/usr/share/doc/psample/copyright`. No headers enter the runtime TAR. Existing upstream license notices are retained verbatim; source comments remain the reference because the selected repository has no COPYING file. The compressed manual uses upstream `rules_gzip`, the existing pinned pigz execution tool, and `--no-name`.

## Validation and maintenance

Native AMD64 and ARM64 Trixie are the declared matrix. The installed-package test checks paths, ownership, modes, symlinks, gzip metadata, SONAME/NEEDED entries, RELRO/BIND_NOW hardening, absence of build RPATHs, build IDs, debuglink CRCs, and GDB source/types with a negative control. A small consumer links the exported SDK, is copied away from Bazel library symlinks, and runs against the installed library.

The installed CLI receives sample and group-update netlink messages through a test-only replacement of the kernel transport functions. The actual installed library performs attribute parsing and callbacks; the actual CLI formats the sampled payload and notifications. Tests cover sample/config filtering, group listing, and a failed family-open operation. This is a declared protocol fixture, not proof of live kernel or ASIC packet sampling; the Docker integration retains that acceptance boundary.

Preserve existing source behavior when maintaining the overlay. The selected header declares `psample_get_log_level`, while the selected implementation exports `get_log_level`; this pre-existing upstream mismatch is not renamed by the migration.
