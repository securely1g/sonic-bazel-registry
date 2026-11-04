# Register the landed cumulative FIPS source

This entry selects `sonic-fips` maintained `main` commit
`15fcb926a302059ec379f0c2fd15eb3d88bda4c9`, the first-parent merge of
[FIPS #12](https://github.com/securely1g/sonic-fips/pull/12).
The complete source tree and all nine submodule revisions equal published
`.4-ef423363`; that earlier pin names the merge's second parent rather than the
landed integration commit. Published `.4` and every earlier entry are preserved.

| Consumer input | Published `.4` | This `.5` registration |
| --- | --- | --- |
| Exact cumulative source | Review head `ef423363`, reachable through a merge's second parent | Landed first-parent commit `15fcb926`, with identical source files, modes and submodules |
| Native build/test contract | 18 output targets and six tests on AMD64/ARM64 | The same complete presubmit, byte-for-byte |
| Explicit FIPS selection in Teamd, Libteam and FRR | Earlier consumers pin `d1`/`e910`; current staging selects `.4` | A coordinated direct dependency and version override can select the landed cumulative source |

The cumulative source retains the compiler response-file, OpenSSH source-SDK,
SymCrypt build-path and deterministic timestamp repairs from FIPS #9–#15.
The numeric revision is advanced because `.4` is already published; no source
producer, dependency minimum, crypto behavior or packaging target changes.
The only source patch changes the module's version string.

The ordinary consumer continues to select published Distroless `.16` and its
existing infrastructure contract. Teamd/Libteam/FRR and final image catalog
adoption are separate validation boundaries: update both direct dependencies
and explicit overrides, verify the fetched module and run the affected native
checks. Live SDK and image inputs remain frozen until their current phases
finish. No full image or sealed-crypto reproducibility claim follows from
source-tree equality.

Archive integrity, first-parent provenance and exact source/registration
comparisons are required before publication. Fresh registry-fetched/native
acceptance remains pending for this source identity. No DEB output is added.
