# Shared GCC launcher for large foreign builds

Register the source from [build-infra #56](https://github.com/securely1g/sonic-build-infra/pull/56), including its prerequisite configure/Libtool support. The only registry patch sets the full module version; the source archive and patch are pinned by SHA-256.

BMv2's source configure probe exceeds Linux's per-string limit when GCC copies its declared include/library search list into `COLLECT_GCC_OPTIONS`. The shared adapter forwards the visible native include group through a private compiler launcher, retaining effective include precedence and all linker inputs/order. Response-file invocations pass through unchanged. No additional adapter inputs or legacy Make changes are required.

Version `0.0.19` ensures dependency resolution selects this behavior over the earlier `0.0.18` registration. That existing entry is preserved. The native AMD64/ARM64 registry matrix exercises the C/C++ E2BIG reproducer, successful adapted compilation/execution, competing-header and response-file semantics, exact linker/output operands and the existing real Autoconf/Libtool library consumer, alongside existing compiler/runtime/debug checks.

This Draft depends directly on build-infra #56. Land its source prerequisite chain, repin this entry to the maintained source commit and pass both native source and registry checks before Ready. BMv2 registry #89 is the concrete failing consumer; the source producer pins currently select the older adapter until the coherent dependency update lands. Runtime/debug TAR consumers do not require Debian package generation.
