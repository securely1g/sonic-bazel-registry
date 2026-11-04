# SONiC FIPS cumulative candidate `0.0.4`

Registers landed source commit `ef423363e8fd50358f0aa2a8a20d3e08d4450a56`
from [FIPS #12](https://github.com/securely1g/sonic-fips/pull/12). Its tree
is identical to `sonic-fips` `main@15fcb926a302` (the merge commit of #12),
so this one entry carries every fix landed on FIPS `main`:

| FIPS PR | Change |
| --- | --- |
| [#9](https://github.com/securely1g/sonic-fips/pull/9), [#10](https://github.com/securely1g/sonic-fips/pull/10) | Kerberos/OpenSSH debug paths and OpenSSL compiler metadata normalization (published through `0.0.3-401a5d7e…`) |
| [#11](https://github.com/securely1g/sonic-fips/pull/11) | SymCrypt provider/engine build-path RPATH padding (published as `0.0.3-44d18af6…` by registry #184) |
| [#13](https://github.com/securely1g/sonic-fips/pull/13) | Declared source paths in SymCrypt assembly debug data (not registered before this entry) |
| [#14](https://github.com/securely1g/sonic-fips/pull/14) | Ordered response files for large OpenSSH and Kerberos compiler flag lists (previously proposed by closed registry #194) |
| [#15](https://github.com/securely1g/sonic-fips/pull/15) | OpenSSH selects the source OpenSSL SDK with `--with-ssl-dir`, so Debian 3.5.6 headers are no longer mixed with the source 3.5.7 library |
| [#12](https://github.com/securely1g/sonic-fips/pull/12) | SymCrypt build metadata uses the pinned source timestamp |

The minor version is bumped to `0.0.4` so Bzlmod selects this entry over
every published `0.0.3-<sha>` without relying on SHA-suffix ordering.

The ordinary native AMD64/ARM64 consumer selects published Distroless
`0.9.4.sonic.16` (registry #200, which fixes target-CPU header selection);
the owner's module minimum remains `.13`. All 18 runtime/debug/SDK/metadata
outputs and the installed/integration tests are retained, and SymCrypt's new
`timestamp_test` from #12 is added to the validation targets.

No crypto, entropy, integrity sealing or DEB output is changed. Sealed-core
and whole-image reproducibility remain separate, unproven claims. Consumers
with an explicit FIPS `single_version_override` must update it to this direct
pin and verify the fetched MODULE.
