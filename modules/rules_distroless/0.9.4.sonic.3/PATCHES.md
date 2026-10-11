# Patch provenance

This version uses the checksum-pinned upstream rules_distroless 0.9.4 archive.
It preserves the include-fragment fix and the pkg-config whitespace patch from
[the 0.9.4.sonic.2 candidate](https://github.com/securely1g/sonic-bazel-registry/pull/54).

`0004-pkgconfig-whitespace.patch` is copied from
[sonic-build-infra 7755cb7](https://github.com/securely1g/sonic-build-infra/blob/7755cb7ee3efd0eb97d16721bb64c070141f6e96/third_party/rules_distroless/0001-pkgconfig-whitespace.patch).
`0005-multiarch-headers.patch` is copied from
[sonic-build-infra f3d9abf](https://github.com/securely1g/sonic-build-infra/blob/f3d9abf5a7d652af22575388c888ba1cd11ed26f/third_party/rules_distroless/0001-multiarch-headers.patch).

The module-version and registry-CI patches select this version and expose lazy
validation repositories. CI fetches existing pinned Debian packages; it does not
create DEB packages. The new Lua test compiles its real public headers and checks
that Debian's selected multiarch header matches the native CPU. It does not test
Lua interpreter execution; the eventd consumer runs its original native suites.
