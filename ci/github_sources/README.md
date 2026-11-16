# GitHub inputs for Bazel

Use the approved private mirror for Debian inputs. Use GitHub for other mirrored
archives and build tools; another location, including a fallback or a one-time
acquisition origin, needs explicit user approval. Keep existing scoped approvals
and unrelated inherited transports separate from this change.

`ci/github_sources.py` supplies locked files to Bazel's standard `--distdir`.
Package data lives in JSON manifests, so another package does not need another
downloader or workflow branch. The reader needs no GitHub token and never executes
downloaded files. It uses existing upstream GitHub assets when available.

## The Cosmos example

[Registry #238](https://github.com/securely1g/sonic-bazel-registry/pull/238) recovered
three inputs for AMD64 `libteam@1.31.0.sonic.1` from the official
[Cosmos 4.0.2 release ZIP](https://github.com/jart/cosmopolitan/releases/download/4.0.2/cosmos-4.0.2.zip).
Its original individual `cosmo.zip` requests could fail before compilation. The
ZIP already lives on GitHub; there is no need to republish these tools.

The shared manifest also includes `ape-aarch64.elf` and `ape-arm64.elf` so ARM64
consumers receive both declared launcher names from the same upstream ZIP.

| Input or action | Before | This reader |
| --- | --- | --- |
| `assimilate`, `ape-x86_64.elf`, `gzip.ape` | A Cosmos-specific script has the filenames and checksums in code | `cosmos-4.0.2.json` selects the same ZIP members and original hashes |
| Select a source set | A libteam/AMD64 conditional in a workflow | `catalog.json` matches module, version and execution architecture |
| Add another package | Another special-case downloader | Add a direct-file or ZIP-member manifest and a catalog entry |
| A GitHub redirect leaves GitHub infrastructure | Generic redirect handling can contact another service | Reject it before making that request |
| Any selected file fails verification | The Cosmos-specific helper stops libteam validation | The shared helper stops any selected consumer before Bazel |

The ZIP is 402711738 bytes (GitHub asset ID 218247825). Upstream publishes no
whole-ZIP digest. Each selected member's original size and SHA256 are the
integrity boundary, not the release tag or the unverified rest of the ZIP:

| ZIP member → distdir basename | Bytes | SHA256 |
| --- | ---: | --- |
| `bin/assimilate` → `assimilate` | 656101 | `93f63aac14046bc2530e4f98ff4dc7ade2e3a3aa3136ced3db598bf6b0026edc` |
| `bin/ape-x86_64.elf` → `ape-x86_64.elf` | 9249 | `7c1cf8b24e1b6dd6ad7da3817045d582ada146b4d6ec0c6a45bea830e3a65f4d` |
| `bin/ape-aarch64.elf` → `ape-aarch64.elf` | 8296 | `877ccbd465243065426cb4a3cab4351acad918649f8656556bb604882eead08f` |
| `bin/ape-arm64.elf` → `ape-arm64.elf` | 8296 | `877ccbd465243065426cb4a3cab4351acad918649f8656556bb604882eead08f` |
| `bin/gzip.ape` → `gzip.ape` | 980684 | `c4b948a5befb1fc8bdb5d808636e69901223e01848c38a56b9c62195b743cdff` |

These hashes come from `ape-v1.0.1/ape/cosmos/4.0.2.json` in the
[existing GitHub APE mirror](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/ape-v1.0.1.tar.gz),
verified against the SHA512 in
[BCR's pinned APE source record](https://github.com/bazelbuild/bazel-central-registry/blob/0d194cb3d4860f5cd400c5c1182b086b742a66f4/modules/ape/1.0.1/source.json).
The original member URLs are provenance, not a reader fallback.

## Use locally or in CI

From the registry checkout:

```sh
python3 ci/github_sources.py \
  --manifest ci/github_sources/cosmos-4.0.2.json \
  --distdir /tmp/sonic-cosmos-inputs \
  --cache-dir /tmp/sonic-github-downloads \
  --receipt /tmp/sonic-cosmos-inputs.json
# Only after preparation succeeds, add this to the normal Bazel command:
bazel build --distdir=/tmp/sonic-cosmos-inputs //your:target
```

The final target is illustrative; the real registered consumer is
`libteam@1.31.0.sonic.1`, proposed in
[registry #236](https://github.com/securely1g/sonic-bazel-registry/pull/236).
That registration is not added or published by this transport change. The catalog
supplies the unchanged tools for native AMD64 and ARM64 execution of libteam.
These selectors do not add architecture coverage to the module's presubmit
configuration.
`registry_ci.py run` adds the distdir before dependency preparation, compilation,
tests and queries, while retaining `private_mirrors.py` and its downloader config.
Execution architecture matters: a future ARM64 target built on AMD64 still uses
the AMD64 host tools. This does not itself enable new cross-build coverage.

For standalone reuse, `--repository-cache` can point to an existing Bazel
repository cache. The helper rechecks size and SHA256 before reusing a distdir
file, repository-cache file or downloaded asset. Registry CI uses a separate
distdir for each manifest's SHA256 to avoid basename collisions between versions.
Receipts under `ci-artifacts/github-sources/` record the manifest hash, canonical
URLs, file hashes and which cache or GitHub supplied each file.

## Add an input set

1. Establish the exact required bytes and original trusted size/hash. Confirm a
   suitable upstream GitHub asset contains them. A checksum calculated only from
   an unverified replacement is not provenance.
2. Add a schema-version-1 manifest beside `cosmos-4.0.2.json`. A `file` source has
   a source SHA256 and one output with the same size/hash. A `zip` source names
   every selected member using `path`, `name`, `size`, `sha256` and `provenance`;
   include a whole-source SHA256 when one is independently established. The
   existing Cosmos manifest is the complete ZIP example.
3. Add an exact module/version/execution-architecture selector to `catalog.json`.
   Keep transport data here rather than changing published module recipes.
4. Run the helper tests and the actual consumer's applicable validation. Preserve
   private-mirror settings and original package/module versions.

The reader accepts named GitHub release assets, full-commit raw files and
full-commit codeload archives. Redirects are restricted to explicit GitHub
delivery hosts. It rejects URL credentials, custom ports, lookalike domains,
unsafe paths, duplicate outputs/members, linked or encrypted members, and
size/hash mismatches. Assets and files are bounded to 2 GiB. ZIP support is
single-part, non-ZIP64, stored/deflated members; central-directory metadata is
bounded. It does not unpack arbitrary archive paths. Files are individually
replaced atomically after the complete set verifies; an OS write failure can
leave a subset of verified files, and the caller must not continue after failure.

If no suitable GitHub asset exists, a separate publication step may upload
verified local, redistributable files to the existing SONiC GitHub mirror release.
Retain provenance/licenses, use immutable identities, reject mismatched existing
assets and verify downloads after publication. Acquiring bytes from any other
host first still requires approval. This reader neither uploads nor republishes
assets, and never silently falls back to another service.

## Validation boundary

`--distdir` is not a network firewall for the rest of a build. Bazel can fall back
to declared URLs if inputs are later removed or no longer match; arbitrary
repository subprocesses also have their own networking. This reader verifies the
selected set before invocation and has no remote fallback. It does not claim to
migrate or constrain unrelated legacy download paths.

`ci/tests/github_sources_bazel_integration.py` verifies real Bazel reuse with
fresh output/cache directories and `--repository_disable_download`, including
missing/corrupt-input rejection. It queries exported files without executing the
downloaded tools. Bazel 8.5.1 checks distdir before that download-disable guard;
its registry metadata and repository subprocess traffic are outside the guard.
See [DownloadManager](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/bazel/repository/downloader/DownloadManager.java)
and the [distdir reference](https://bazel.build/reference/command-line-reference#flag--distdir).
Transport evidence does not establish a native libteam TAR or SONiC image build.
