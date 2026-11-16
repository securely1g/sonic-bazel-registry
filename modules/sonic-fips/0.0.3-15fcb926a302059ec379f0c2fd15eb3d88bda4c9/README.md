# Register the landed cumulative FIPS source

This entry selects `sonic-fips` maintained `main` commit
`15fcb926a302059ec379f0c2fd15eb3d88bda4c9`, the first-parent merge of
[FIPS #12](https://github.com/securely1g/sonic-fips/pull/12), as
`0.0.3-15fcb926a302059ec379f0c2fd15eb3d88bda4c9`. The `0.0.3` prefix matches
[the source module](https://github.com/securely1g/sonic-fips/blob/15fcb926a302059ec379f0c2fd15eb3d88bda4c9/MODULE.bazel#L1-L4).

SONiC's source-built base image consumes this module's OpenSSL, Kerberos and
SymCrypt runtime TARs, for example
`@sonic_fips//openssl:libssl3t64_pkg` and `@sonic_fips//symcrypt:runtime`,
through `//dockers/docker-base-trixie:docker-base-trixie`.
[Libteam PR #162](https://github.com/securely1g/sonic-buildimage/pull/162) and
[FRR PR #163](https://github.com/securely1g/sonic-buildimage/pull/163) currently
select the earlier unpublished `.5-15fc...` spelling in frozen review catalogs;
adopting this corrected entry requires updating their direct dependency,
root version override and temporary catalog together.

| Consumer input | Published `.4-ef423...` | This `.3-15fc...` registration |
| --- | --- | --- |
| Exact cumulative source | Review head `ef423363`, the merge's second parent | Landed first-parent commit `15fcb926`, with identical source files, modes and all nine submodules |
| Registry version prefix | Published `0.0.4` entry, preserved unchanged | Source module's declared `0.0.3`, followed by the full landed source commit |
| Native build/test contract | 18 output targets and six tests on AMD64/ARM64 | The same complete presubmit, byte-for-byte |

The cumulative source retains the compiler response-file, OpenSSH source-SDK,
SymCrypt build-path and deterministic timestamp repairs from FIPS #9–#15.
The only source patch adjusts the module's version string to the full registry
identity; its header records the reason and source provenance. Published `.4`
and every earlier entry remain available unchanged.

Keep consumers' direct dependency and explicit root override aligned. A commit
suffix is not a chronological version, and a higher version request elsewhere
can otherwise select another entry. The registry's routine `--latest` CI still
selects published `.4`; PR validation selects this changed `.3` entry explicitly.
No published entry is renamed, removed or yanked to change that ordering.

The standalone presubmit retains published Distroless `.16` and the existing
infrastructure contract. Registry validation of the corrected identity and
consumer adoption are separate acceptance boundaries. Existing results for the
previous `.5` spelling must not be relabeled as results for this entry. No DEB
output is added, and source-tree equality alone does not establish a successful
full image build or sealed-crypto reproducibility.
