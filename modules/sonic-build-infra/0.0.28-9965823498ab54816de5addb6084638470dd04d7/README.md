# Shared build-infra 0.0.28

This entry registers `sonic-build-infra@0.0.28-9965823498ab54816de5addb6084638470dd04d7` from [build-infra master](https://github.com/securely1g/sonic-build-infra/commit/9965823498ab54816de5addb6084638470dd04d7).

| Consumer | Change since 0.0.27 |
| --- | --- |
| ARM64 target runtimes | The execution-platform Python prepares target payloads, checks their ELF architecture and passes control to the target loader. This fixes the original libyang interactive prompt timeout. [Source #88](https://github.com/securely1g/sonic-build-infra/pull/88) |
| Sysmgr package inventory | A public metadata alias keeps its own repository identity when the underlying JSON comes from another repository. [Source #89](https://github.com/securely1g/sonic-build-infra/pull/89) |
| Shared APT lock | The production lock covers the image and component request groups, including libteam, FRR, and the FRR and Net-SNMP Bookworm dependencies. Trixie and Bookworm keep their separate package selections. [Source #90](https://github.com/securely1g/sonic-build-infra/pull/90) · [APT lock reconciliation](https://github.com/securely1g/sonic-build-infra/pull/93) |
| PI and native library consumers | Configure can transport long linker flags through a response file. Native GCC links retain ordered `-Xlinker` search pairs and use parameter files for long commands. [Source #91](https://github.com/securely1g/sonic-build-infra/pull/91) · [Source #92](https://github.com/securely1g/sonic-build-infra/pull/92) |

The registry presubmit selects 40 build targets and 46 tests on both native Trixie architectures. AMD64 also builds the two DocBook targets and runs the DocBook test and its two kernel cross-compiler tests, for 42 builds and 49 tests. The source declares DocBook for AMD64 only. Both architectures exercise the native kernel tools. Two of those tests validate the lock updater and the packaged Bookworm lock. The other tests cover the runtime launcher, public metadata aliases, paired linker flags, runtime and debug TARs, and the declared tools. Bookworm library imports run in the source repository's Bookworm validation. The image repositories validate their own installation paths and inventory.

The archive, version patch, visibility patch and registry-only fixtures are pinned in [source.json](source.json). [Patch details](PATCHES.md)
