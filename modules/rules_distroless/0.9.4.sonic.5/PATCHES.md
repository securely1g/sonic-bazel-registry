# Patch provenance

This version uses the checksum-pinned upstream rules_distroless 0.9.4 archive.
It retains all production fixes from
[0.9.4.sonic.4](https://github.com/securely1g/sonic-bazel-registry/pull/63):
include fragments, pkg-config whitespace, target-specific multiarch headers and
public pkg-config files.

- `0004-pkgconfig-whitespace.patch`: [sonic-build-infra 7755cb7](https://github.com/securely1g/sonic-build-infra/blob/7755cb7ee3efd0eb97d16721bb64c070141f6e96/third_party/rules_distroless/0001-pkgconfig-whitespace.patch).
- `0005-multiarch-headers.patch`: [sonic-build-infra f3d9abf](https://github.com/securely1g/sonic-build-infra/blob/f3d9abf5a7d652af22575388c888ba1cd11ed26f/third_party/rules_distroless/0001-multiarch-headers.patch).
- `0006-pkgconfig-files.patch`: [sonic-build-infra 5071fef](https://github.com/securely1g/sonic-build-infra/blob/5071fef717deac95ccceff851ce7d808667c41e6/third_party/rules_distroless/0001-pkgconfig-files.patch).

- `0007-concrete-packages.patch`: [sonic-build-infra 12a67fd](https://github.com/securely1g/sonic-build-infra/blob/12a67fd2bc292af156f40372274c9cb3011e5c23/third_party/rules_distroless/0001-concrete-packages.patch).

The existing `:pkgconfig` targets export the importer's discovered library metadata,
including aliases such as `lua-5.1.pc`, through direct package, selected package
and dependency-set interfaces. They preserve the original bytes and filter
transitive packages by target architecture. Consumers use their declared
pkgconf tool and relocate its path variables to their existing dependency
staging directory.

The module-version and registry-CI patches select this version and expose lazy
validation repositories. CI fetches existing pinned Debian packages; it does
not create DEB packages. All seven previous tests remain, including comparison of pkg-config outputs
with the original Lua development TAR. The eighth exercises concrete-package
preference and virtual fallback through the actual upstream resolver.
