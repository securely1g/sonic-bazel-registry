# Syncd runtime service links

Registers [Sairedis #7](https://github.com/securely1g/sonic-sairedis/pull/7)
at source commit `aba7b649177fbdc2a650807410443d6dd4cfa929`.
[Buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13) will consume
`@sonic_sairedis//syncd:syncd_pkg` directly without reconstructing these links in
the image. The consumer update is separate.

| Runtime paths | Published package | Candidate |
| --- | --- | --- |
| `etc/rc0.d/K01syncd`, `etc/rc6.d/K01syncd`, `etc/rcS.d/S01syncd` | Missing | Root-owned symlinks to `../init.d/syncd`, mode `0777`, timestamp `0` |

The links are in the existing producer init TAR for both ordinary VS and DASH
builds. Existing source archive-contract tests verify their raw headers and
installed targets. No installation scripts run while packaging.

This candidate carries forward published `0.0.2-54233eede3bb2eb319f6041bc8329586483012d0`'s
native AMD64/ARM64 build and test targets unchanged, including runtime/debug
packages and metadata. Dependency selections and published entries are unchanged.
The numbered module-version patch changes source version `0.0.2` to this exact
candidate version.

Keep the registry PR Draft until Sairedis #7 merges, then refresh to the
maintained-branch source commit before marking Ready.
