# iproute2 native Bazel build

Debian 6.15.0-1 source packaging and the SONiC bridge FDB protocol patch are
prepared in order from fixed archives by sonic-build-infra `prepared_source`.
Bazel compiles C sources directly with native `cc_library` and `cc_binary` rules.
Bison/Flex parsers and netem distribution tables have explicit generation actions.

Public interfaces remain `:iproute2_pkg`, `:iproute2_pkg.debug_symbols`,
`:iproute2_config`, `:runtime_packages.json`, and `:iproute2_package_test`.
The runtime TAR preserves the existing uncompressed manual-page interface,
merged-/usr paths, 15 programs, routel, configurations, examples and links.
The package test exercises parser success/failure, dynamic handlers, SONiC and
Debian patch behavior, installed libraries, and matching debug symbols.

Target platforms are x86_64 and aarch64 Trixie; execution tools follow the host
platform. Native runtime tests require a matching target execution environment.
Debian's root-only machine-isolated upstream suite remains outside build-time
test selection as specified in debian/rules.

The registry fetch supplies the module entry tree from the upstream archive.
The prepared source repository independently combines that same fixed archive
with Debian packaging and applies the ordered patches. Archive downloads may
reuse Bazel's checked cache, but this design still performs two extractions;
it does not claim to remove duplicate source preparation. Compilation and
installation consume only the patched prepared repository.

This native build consumes the published sonic-build-infra registration
`0.0.28-9965823498ab54816de5addb6084638470dd04d7`, selecting source commit
`9965823498ab54816de5addb6084638470dd04d7`.
The registered recipe fixes the source archive and module-version patch.
All required dependency entries are available on registry main.
