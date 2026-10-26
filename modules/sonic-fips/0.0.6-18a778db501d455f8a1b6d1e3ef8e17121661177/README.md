# OpenSSH producer installation metadata

Registers [FIPS #8](https://github.com/securely1g/sonic-fips/pull/8) at source
`d1a2c8f692d4197295269ed445022c3890b0f1a6`, its squash commit on maintained `main`. The downloaded
source tree matches the source revision validated below. The previously published
`0.0.3-0565bc0426dde6a1e7c495de17707c9557f843a9` entry stays unchanged.

[Buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13) consumes
`@sonic_fips//openssh:openssh_client_pkg` for its Syncd image. The new producer
TAR carries `usr/bin/ssh-agent` with mode `02755`, uid 0 and gid 104 (`_ssh`),
and the user socket enablement link at
`etc/systemd/user/sockets.target.wants/ssh-agent.socket` pointing to
`/lib/systemd/user/ssh-agent.socket`. The old producer emitted `0755` root:root
and omitted that link, requiring image-side installation changes. Consumers
must provide `_ssh` GID 104 and preserve producer ownership and modes.
`ssh-keysign` stays `04755`; the graphical-session service link is unchanged.

[Source CI](https://github.com/securely1g/sonic-fips/actions/runs/40285998940)
passed the original upstream/client and package tests on native AMD64 and ARM64.
Both actual runtime TARs were checked against their same-run receipts for the
new owners, mode and socket link. This does not establish the final Syncd image.

The registration inherits the previous entry's entire native AMD64/ARM64
presubmit configuration unchanged: all OpenSSL, OpenSSH, Kerberos and SymCrypt
runtime/debug targets, generated package metadata, package tests and the
OpenSSL/SymCrypt integration test remain selected. The existing module-version
patch is adapted only to identify the new full source version. The downloaded
archive hash and patched MODULE.bazel were verified. No DEB is added.
