# SONiC PINS (`sonic-pins`)

Registers `sonic-pins@0.0.2-8b93535e1229290a4efd859d8934bf9014715133` (`securely1g/sonic-pins#5`, commit `8b93535e1229290a4efd859d8934bf9014715133`) for the `docker-sonic-p4rt` OCI image.

## Exported targets

- `@sonic-pins//p4rt_app:p4rt_runtime`: Native OCI deployment TAR containing the five stripped P4RT binaries (`p4rt`, `p4rt_program_table`, `p4rt_read`, `p4rt_set_forwarding_pipeline`, `p4rt_write`).
- `@sonic-pins//p4rt_app:p4rt_runtime.debug_symbols`: Paired detached `.build-id/*.debug` symbols for those five executables.
- `@sonic-pins//p4rt_app:runtime_packages.json`: Producer package metadata (`sonic-p4rt`).
- `@sonic-pins//p4rt_app:runtime_package_test`: External consumer contract test checking TAR/layout, ELF hardening, dynamic linking against `libswsscommon.so.0` and `libnl3` (`libnl-3.so.200`, `libnl-genl-3.so.200`), zero defined netlink symbols, detached GDB symbol lookup, and metadata hashes/dependencies.

## Registry patch

- `patches/0001-module-version.patch`: Sets `version = "0.0.2-8b93535e1229290a4efd859d8934bf9014715133"` in `MODULE.bazel` to match this registry entry.
