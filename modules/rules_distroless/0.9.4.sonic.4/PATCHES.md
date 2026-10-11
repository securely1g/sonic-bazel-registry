# Patch provenance

This version uses the checksum-pinned upstream rules_distroless 0.9.4 archive.
It retains all production fixes from
[0.9.4.sonic.3](https://github.com/securely1g/sonic-bazel-registry/pull/59):
include fragments, pkg-config whitespace, and target-specific multiarch headers.

- `0004-pkgconfig-whitespace.patch`: [sonic-build-infra 7755cb7](https://github.com/securely1g/sonic-build-infra/blob/7755cb7ee3efd0eb97d16721bb64c070141f6e96/third_party/rules_distroless/0001-pkgconfig-whitespace.patch).
- `0005-multiarch-headers.patch`: [sonic-build-infra f3d9abf](https://github.com/securely1g/sonic-build-infra/blob/f3d9abf5a7d652af22575388c888ba1cd11ed26f/third_party/rules_distroless/0001-multiarch-headers.patch).
- `0006-pkgconfig-files.patch`: [sonic-build-infra 5071fef](https://github.com/securely1g/sonic-build-infra/blob/5071fef717deac95ccceff851ce7d808667c41e6/third_party/rules_distroless/0001-pkgconfig-files.patch).

The new `:pkgconfig` targets export the importer's discovered library metadata,
including aliases such as `lua-5.1.pc`, through direct package, selected package
and dependency-set interfaces. They preserve the original bytes and filter
transitive packages by target architecture. Consumers use their declared
pkgconf tool and relocate its path variables to their existing dependency
staging directory.

The module-version and registry-CI patches select this version and expose lazy
validation repositories. CI fetches existing pinned Debian packages; it does
not create DEB packages. All previous six tests remain. A seventh compares the
new outputs from all three interfaces with the original Lua development TAR,
including every metadata alias and the native architecture's library directory.
