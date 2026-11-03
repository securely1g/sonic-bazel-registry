# Select Debian headers for the target CPU

`0.9.4.sonic.16` fixes the public header interface used by SONiC source
builds. Debian `linux-libc-dev` 6.12.96-1 has `Architecture: all` and ships
22 CPU-specific header directories in one archive. The previous importer
exported all those directories alphabetically. On AMD64, it found ARM64's
`asm/unistd.h` first and compiled OpenSSL's AF_ALG engine with
`__NR_io_setup=0`, which invokes `read` on AMD64 and fails with `EBADF`.
AMD64 requires syscall 206; ARM64 correctly requires syscall 0.

| Input or action | Before | After |
| --- | --- | --- |
| The same Linux header archive, AMD64 target | ARM64 directory precedes AMD64; `io_setup=0` | Only AMD64 multiarch roots are exported; `io_setup=206` |
| The same archive, ARM64 target | Every architecture directory is exported | Only ARM64 multiarch roots are exported; `io_setup=0` |
| Ordinary and pkg-config include paths | All declared paths are exported | Ordinary paths and matching nested multiarch paths retain their order |

The generated `cc_library` selects search paths using Bazel's target CPU,
not the execution host or the Debian archive's `all` label. It retains all
header files and their declared symlink targets. The CPU mapping matches the
existing APT hub: AMD64, ARM64, armhf, i386, ppc64el, mips64el and s390x.
Unsupported multiarch directories are not exported as a fallback.
The package payload and all crypto code and tests remain unchanged.

The concrete consumer is
[FIPS registry #197](https://github.com/securely1g/sonic-bazel-registry/pull/197),
whose native AMD64 OpenSSL integration test fails at `30-test_afalg.t` with
`.sonic.15`. Its ARM64 integration test passes. The source OpenSSH provider
selection in [FIPS #15](https://github.com/securely1g/sonic-fips/pull/15) is a
separate change; this module fixes the shared kernel-header exporter.
Consumer adoption and complete crypto-suite validation remain pending.

## Validation

The independent integration module uses Bazel 8.5.1 and `rules_cc@0.2.22`.
CI retains all seven outputs and 33 tests from published `.sonic.15` and adds:

- An analysis test inspects the actual `CcInfo` of the same imported archive
  under AMD64 and ARM64 target configurations, rejecting foreign include roots.
- A native C test compiles the imported `asm/unistd.h`, checks the correct
  syscall numbers, and creates/destroys a real Linux AIO context. It runs on
  both native CPUs without capability skips.

This produces eight build outputs and 35 tests per architecture. Local/native
and hosted results are pending. The recipe only fetches and extracts existing
checksum-pinned Debian archives; it adds no DEB producer. Complete FIPS crypto
and installed-image acceptance remains the downstream consumer's gate.

The upstream archive is unchanged. Published entries remain unchanged;
patches 0002–0018 are inherited byte-for-byte. Patch 0001 changes only this
candidate's module version and 0019 adds the target header selection and its
lazy test repository. All existing fixtures and test selections are retained.
See [patch provenance](PATCHES.md).
