# Complete registry version comparisons for PR133 prerequisites

These patches compare the complete published version entries with the exact
candidates in [registry #218](https://github.com/securely1g/sonic-bazel-registry/pull/218)
and [registry #221](https://github.com/securely1g/sonic-bazel-registry/pull/221).
They are review evidence only. This branch adds no registry module version or
source change and is not a catalog endpoint for consumer builds.

The baseline is maintained registry commit
`ce3ac4e892e1a28dccd60d54c3a8385ae1c8f163`. The relevant published entries and
module metadata are unchanged since the candidates' original bases. Each patch
compares matching relative paths after copying the published entry into the new
version directory, then applies every delta and the module metadata update.
Unchanged files are inherited by that copy; deleted patches are removed.

## Registry #218

- Published entry: `modules/sonic-build-infra/0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568`.
- Candidate entry: `modules/sonic-build-infra/0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e`.
- Candidate registry commit: `11713fea55f58ae7e9ef561b12c3a06366900c6b`.
- [View colored patch](sonic-build-infra-0.0.26-51c838da-to-0.0.25-3ee15ec9.patch) · [Download raw patch](sonic-build-infra-0.0.26-51c838da-to-0.0.25-3ee15ec9.patch?raw=1).
- Patch SHA-256: `8683bddb62ca7688ff7bda6f6ed17cd6ffcf9baf378fcf253b6942dfea3025fc`.
- Exact reproduced candidate Git tree: `9335f68d5e8286ca2a00cd4398e656e65427d63b`.

Save the raw patch outside the checkout. In a fresh registry checkout, replace
`/absolute/path/sonic-build-infra-0.0.26-51c838da-to-0.0.25-3ee15ec9.patch` with the saved patch's actual absolute path:

```sh
git checkout --detach ce3ac4e892e1a28dccd60d54c3a8385ae1c8f163
test ! -e modules/sonic-build-infra/0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e
cp -a modules/sonic-build-infra/0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568 modules/sonic-build-infra/0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e
git apply --check /absolute/path/sonic-build-infra-0.0.26-51c838da-to-0.0.25-3ee15ec9.patch
git apply /absolute/path/sonic-build-infra-0.0.26-51c838da-to-0.0.25-3ee15ec9.patch
```

The destination must not already exist. `git apply --check` and application were
verified in an isolated baseline checkout. All 11 candidate files and Git
modes reproduce the pinned candidate exactly, and its module metadata matches.
The published entry and all unrelated baseline files remain unchanged.

## Registry #221

- Published entry: `modules/sonic-fips/0.0.4-ef423363e8fd50358f0aa2a8a20d3e08d4450a56`.
- Candidate entry: `modules/sonic-fips/0.0.5-15fcb926a302059ec379f0c2fd15eb3d88bda4c9`.
- Candidate registry commit: `8374b07ca138b98546122186d832544f1b46ac07`.
- [View colored patch](sonic-fips-0.0.4-ef423363-to-0.0.5-15fcb926.patch) · [Download raw patch](sonic-fips-0.0.4-ef423363-to-0.0.5-15fcb926.patch?raw=1).
- Patch SHA-256: `c4cab812d37b69c53e5e3a67f8959365dcae5ff67a20f94d3a0fcf3651a3a0bf`.
- Exact reproduced candidate Git tree: `bff0a107aead3e9c08b353bd0bb56c900abef948`.

Save the raw patch outside the checkout. In a fresh registry checkout, replace
`/absolute/path/sonic-fips-0.0.4-ef423363-to-0.0.5-15fcb926.patch` with the saved patch's actual absolute path:

```sh
git checkout --detach ce3ac4e892e1a28dccd60d54c3a8385ae1c8f163
test ! -e modules/sonic-fips/0.0.5-15fcb926a302059ec379f0c2fd15eb3d88bda4c9
cp -a modules/sonic-fips/0.0.4-ef423363e8fd50358f0aa2a8a20d3e08d4450a56 modules/sonic-fips/0.0.5-15fcb926a302059ec379f0c2fd15eb3d88bda4c9
git apply --check /absolute/path/sonic-fips-0.0.4-ef423363-to-0.0.5-15fcb926.patch
git apply /absolute/path/sonic-fips-0.0.4-ef423363-to-0.0.5-15fcb926.patch
```

The destination must not already exist. `git apply --check` and application were
verified in an isolated baseline checkout. All 5 candidate files and Git
modes reproduce the pinned candidate exactly, and its module metadata matches.
The published entry and all unrelated baseline files remain unchanged.

## Verification scope

The full baseline contained 1,904 files: 1,899 mode `100644` and five mode
`100755`, with no symlinks or gitlinks. Both applications preserved their modes
and contents, except their intentional module metadata update. Recipe archive,
patch and overlay integrity verification was performed separately. Registry
#218's current five CI checks and #221's current six checks pass; consumer
module resolution and final image acceptance remain separate validation steps.

The changed source archive URLs and integrity values are included in each patch.
The registry patches do not contain every source change inside those archives:

- [Infra source revision comparison](https://github.com/securely1g/sonic-build-infra/compare/51c838da6ff57295fde6e0bc3807841cb31a8568...3ee15ec9b4d99d7f8eae3e324cead79b203b451e).
- [FIPS source revision comparison](https://github.com/securely1g/sonic-fips/compare/ef423363e8fd50358f0aa2a8a20d3e08d4450a56...15fcb926a302059ec379f0c2fd15eb3d88bda4c9); the source trees and submodules are identical.

Neither artifact publication nor passing registry CI authorizes merging a PR.
