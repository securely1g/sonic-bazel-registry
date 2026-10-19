# Native shared-library metadata

This version retains every `0.9.4.sonic.5` patch and advertises the `CcInfo`
provider already returned by `so_library` and `cc_deb_library`. Native
`cc_shared_library` can then traverse their dependency graph and retain the
versioned runtime libraries declared by imported Debian packages.

For example, a development import may expose `libhiredis.so` while the runtime
package provides `libhiredis.so.1.1.0` in another directory. The shared-library
consumer needs metadata for both paths. This change preserves that metadata;
it does not rewrite ELF files or change the installed Debian payloads.

Imported Debian libraries still require a suitable runtime environment for
their own indirect dependencies, such as the matching installed runtime
packages. Advertising a provider does not give those libraries a RUNPATH.

[Patch provenance and validation](PATCHES.md) describes the retained fixes
and ten native AMD64/ARM64 regression and integration tests. CI uses Bazel
8.5.1 and imports existing pinned Debian packages without producing DEBs.
