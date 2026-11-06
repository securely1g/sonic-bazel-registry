# Registry CI

Registry CI validates a module as a dependency in a fresh Bazel consumer. It
resolves the module from the proposed registry checkout, then builds the declared
outputs and runs explicit consumer and package tests. This exercises registry
resolution, archive integrity, patch and overlay application, compilation, and
the behavior covered by each module's tests.

The workflow runs on every pull request, pushes to `main`, and manual dispatches.
Pull requests select affected module versions. Changes to the CI implementation
or workflow also test the latest version of each module covered by CI. Pushes and
manual runs test those latest versions by default. To test every configured
historical version, select **all_versions** when manually running the workflow,
or use `plan --all` locally.
Revised unreleased candidates require a validation configuration too.
Published consumer inputs and version directories cannot be removed or rewritten;
standalone documentation and test maintenance is allowed as described below.
Unchanged historical entries without a configuration are not represented as
validated. Documentation-only changes can produce an empty module matrix.
In particular, `modules/<name>/README.md` and permitted documentation-only edits
inside a published version do not select a version. Documentation changes in an
unpublished candidate still validate that candidate.

`Registry CI` is the stable aggregate check intended for branch protection. It
passes only when planning, both native unit jobs, the explicit cross fixture,
and every selected module job pass. A skipped module matrix is accepted only
after successful planning explicitly selected no jobs. Adding the workflow does not itself change
repository branch-protection settings.

## Verified source mirrors

### Cosmos inputs for libteam AMD64 validation

The AMD64 `libteam@1.31.0.sonic.1` job supplies three unchanged Cosmos 4.0.2
inputs used by BCR `ape@1.0.1` through Bazel's standard `--distdir`. This addresses
the [original endpoint connection resets](https://github.com/securely1g/sonic-bazel-registry/actions/runs/41989630213/job/127118582713)
that stopped archive analysis before compilation. No module, tool version,
integrity, build target or test changes are required.

The [following native job](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42006635670/job/127181766520)
verified both initial members from the official ZIP, then failed fetching
`gzip.ape` from the same original host for `libteam_utils_runtime`. Add that
unchanged compressor to the same distdir; its locked SHA256 and exact bytes
also match the official ZIP. That failed build does not establish complete
library or image acceptance.

[`prepare_cosmos_distdir.py`](prepare_cosmos_distdir.py) first reuses valid files
in its distdir or an explicitly supplied Bazel repository cache. On a miss it
uses a cached release ZIP, or downloads the complete official
[`cosmos-4.0.2.zip`](https://github.com/jart/cosmopolitan/releases/download/4.0.2/cosmos-4.0.2.zip)
(asset 218247825, 402,711,738 bytes). It reads only `bin/assimilate`,
`bin/ape-x86_64.elf` and `bin/gzip.ape` with standard Python ZIP tooling. All members must match
the checked-in sizes observed in the official ZIP and the SHA256 values
pinned by APE's `ape/cosmos/4.0.2.json` before any
is published under its exact URL basename. Members are never executed by this
helper. Unexpected sizes, duplicate members, symlinks and checksum failures
stop preparation; no unverified fallback is used. The ZIP has no upstream
whole-file digest, so the member hashes are the integrity boundary.

| Distdir basename | Bytes | Locked SHA256 |
| --- | ---: | --- |
| `assimilate` | 656101 | `93f63aac14046bc2530e4f98ff4dc7ade2e3a3aa3136ced3db598bf6b0026edc` |
| `ape-x86_64.elf` | 9249 | `7c1cf8b24e1b6dd6ad7da3817045d582ada146b4d6ec0c6a45bea830e3a65f4d` |
| `gzip.ape` | 980684 | `c4b948a5befb1fc8bdb5d808636e69901223e01848c38a56b9c62195b743cdff` |

The workflow invokes the helper from the same checked-out revision as the
validation runner. Its distdir and ZIP cache are siblings of the fresh Bazel
work directory, and the JSON receipt is retained in the existing CI artifact.
This workflow does not restore a persistent cache across jobs. Other module
versions and architectures keep their existing setup; another caller can use
the helper's CLI without introducing a new module-validation mechanism.

While the helper PR is Draft, only the same-repository branch
`codex/registry-cosmos-distdir` with its exact five-file transport scope suppresses
the module matrix after normal policy planning. Both existing runner test suites
and the independent ARM cross compiler/runtime fixture still run. The full planner
otherwise selects 66 module jobs across native AMD64, native ARM64 and ARM64 cross
execution for this shared CI change; those broad regressions remain unvalidated by the
Draft guard. **Remove the guard before marking the PR Ready.** The stacked
libteam registration will exercise the actual helper with its ordinary native
outputs and tests; focused helper tests alone do not establish that acceptance.

### Archive and package mirrors

The runner passes Bazel's standard `--experimental_downloader_config` with
[`source_mirrors.cfg`](source_mirrors.cfg) to dependency preparation, builds,
tests and output queries. Rewrites match only the archive and binary-package
URLs and the exact dated package indexes described below; registry order, module versions, source recipes and
integrity values stay unchanged.

The five ARM-hosted BCR archives use verified copies in this repository's
[source-mirror release](https://github.com/securely1g/sonic-bazel-registry/releases/tag/ci-source-mirrors-20261104)
first, with each original GitLab release URL retained as the next candidate:

| BCR module | Release asset |
| --- | --- |
| `ape@1.0.1` | `ape-v1.0.1.tar.gz` |
| `download_utils@1.0.1` | `download_utils-v1.0.1.tar.gz` |
| `rules_coreutils@1.0.1` | `rules_coreutils-v1.0.1.tar.gz` |
| `rules_gzip@1.0.0` | `rules_gzip-v1.0.0.tar.gz` |
| `toolchain_utils@1.0.2` | `toolchain_utils-v1.0.2.tar.gz` |

Each copy must satisfy the original BCR SHA512 integrity. This avoids the
[ARM GitLab release endpoint failures](https://github.com/bazelbuild/bazel-central-registry/issues/9973)
without discarding the upstream source. Bazel 8.5.1's
[URL rewriter](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/bazel/repository/downloader/UrlRewriter.java)
collects matching replacements in configuration order; its
[downloader](https://github.com/bazelbuild/bazel/blob/8.5.1/src/main/java/com/google/devtools/build/lib/bazel/repository/downloader/HttpDownloader.java)
tries the next candidate after a failed download or checksum mismatch. Other
versions and URLs are unaffected; no global module mirror is enabled.

The exact `gawk-5.3.2.tar.xz` URLs at `mirrors.kernel.org`, `ftp.gnu.org`, and
`ftpmirror.gnu.org` likewise try MacPorts first and retain each original URL as
a fallback. The published source recipe and SHA256
`f8c3486509de705192138b00ef2c00bbbdd0e84c30d5c07d23fc73a9dc4cc9cc` remain unchanged.

Some packages have additional exact-URL candidates before their timestamped
snapshot fallbacks:

| Locked package | Additional candidate |
| --- | --- |
| `libcap-dev_2.75-10+deb13u1+b1_amd64.deb` | Debian content-addressed file |
| `libaudit-dev_4.0.2-2+b2_amd64.deb` | Debian content-addressed file |
| `libcap2_2.75-10+deb13u1+b1_arm64.deb` | Verified GitHub release copy |
| `bash_5.2.37-2+b9_arm64.deb` | Verified GitHub release copy |
| `libcap-dev_2.75-10+deb13u1+b1_armhf.deb` | Verified GitHub release copy |
| `libsqlite3-0_3.46.1-7+deb13u1_amd64.deb` | Verified GitHub release copy |
| `libpcre2-8-0_10.46-1~deb13u1_armhf.deb` | Verified GitHub release copy |
| `libcap2_2.75-10+deb13u1+b1_amd64.deb` | Verified GitHub release copy |
| `libc-bin_2.41-12+deb13u3_arm64.deb` | Debian content-addressed file, then existing CDN fallback |
| `uuid-dev_2.41-5_amd64.deb` | Debian content-addressed file, then existing CDN fallback |
| `libc-ares-dev_1.34.5-1+deb13u1_arm64.deb` | Debian content-addressed file, then the official security CDN |
| `openssl-provider-legacy_3.5.6-1~deb13u2_arm64.deb` | Debian content-addressed file |
| `openssl_3.5.6-1~deb13u2_arm64.deb` | Debian content-addressed file |
| `libc6_2.41-12+deb13u3_arm64.deb` | Debian content-addressed file, then existing CDN fallback |
| `libblkid1_2.41-5_amd64.deb` | Debian content-addressed file, then existing CDN fallback |
| `libpython3.13-dev` 3.13.5-2+deb13u4 (AMD64, ARM64) | Debian content-addressed file, then existing CDN fallback |
| `libtiff6_4.7.0-3+deb13u3_amd64.deb` | Debian content-addressed file |
| `libtiff6_4.7.0-3+deb13u3_arm64.deb` | Debian content-addressed file, then the official security CDN |
| `libmount1_2.41-5_arm64.deb` | Debian content-addressed file, then existing CDN fallback |
| `libgssrpc4t64_1.21.3-5+deb13u1_amd64.deb` | Debian content-addressed file |
| `libxapian30_1.4.29-3_arm64.deb` | Debian content-addressed file, then existing CDN fallback |
| `libssl-dev` 3.5.6-1~deb13u2 (AMD64, ARM64, ARMHF) | Debian content-addressed file |
| `libuuid1` 2.41-5 (AMD64, ARM64, ARMHF) | Debian content-addressed file, then existing CDN fallback |
| `libssl3t64` 3.5.6-1~deb13u2 (AMD64, ARM64, ARMHF) | Debian content-addressed file |
| `libexpat1` 2.7.1-2 (AMD64, ARM64, ARMHF) | Debian content-addressed file, then existing CDN fallback |
| `libfreetype6` 2.13.3+dfsg-1+deb13u1 (AMD64, ARM64) | Debian content-addressed file, then the official security CDN |

These candidates preserve each original APT-lock SHA256. The SHA1 in Debian's
content-addressed URL is only a locator; Bazel still checks the stronger locked
SHA256. The GitHub copies have a [checksum and origin manifest](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/debian-package-mirrors-20261105.json).

The additional [libcap/SQLite origin manifest](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/debian-package-mirrors-libcap-sqlite-20261105.json) records the exact retained `libcap-dev` ARMHF and `libsqlite3-0` AMD64 copies. Their complete public release downloads (408,140 and 914,268 bytes) match the original accepted APT-lock SHA256 and retained cache bytes. SQLite also matches the checked-in image locks; libcap uses retained accepted generated-lock evidence and the exact current failure URL, not a retrieved failed-run lock. The earlier upstream HTTP503/504 and alternate-host TLS failures were not retried. No package was generated or executed; the archive header check was only Debian ar magic, not a cryptographic package signature. The exact routes try the verified copy, then preserve the existing official CDN and original Snapshot fallbacks. Configured-fetch and native acceptance remain pending.

The [PCRE ARMHF origin manifest](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/debian-package-mirror-libpcre2-armhf-20261105.json) records the exact 259,492-byte `libpcre2-8-0` copy selected during [PR196 AMD64 Orchagent analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42104634714/job/127516101054). The current pool returned HTTP404, dated Snapshot and the one content-addressed Snapshot request returned HTTP503, and the one alternate-host request ended with a TLS error. The complete public release download matches the accepted generated-lock SHA256 and retained cache bytes; the same libyang module and exact current failing URL bind the selected input, without claiming a retrieved failed-run lock. GitHub normalized the asset basename from `~` to `.`, so only that exact original URL maps to the observed asset name; the package version and hash are unchanged. Existing CDN/original fallbacks remain. The other 19 warnings in the failed query and 53 earlier-only warnings are outside this change. No package was generated or executed; configured-fetch and consumer acceptance remain pending.

The additional [libcap2 AMD64 origin manifest](https://github.com/securely1g/sonic-bazel-registry/releases/download/ci-source-mirrors-20261104/debian-package-mirror-libcap2-amd64-20261105.json) binds the 28,988-byte release copy to PR163’s current checked-in image lock and full cache SHA256. [Sysmgr analysis in its AMD64 archive job](https://github.com/securely1g/sonic-buildimage/actions/runs/42117110267/job/127559563902) reached this package after earlier successful build phases, then failed with pool HTTP404 and dated Snapshot HTTP503; the one official content request also returned HTTP503. The complete public copy matches the original locked bytes. The exact route retains the official CDN and original Snapshot fallbacks, with package identity and SHA256 unchanged. Configured-fetch and consumer acceptance remain pending; no package was generated or executed.

[PR196 native FRR analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42127542383/job/127595462127) could not obtain any format of the dated `trixie-updates/main/binary-arm64/Packages` index: xz/gz/bz2 returned HTTP 503 and plain Packages returned HTTP 404. One later original-xz request returned HTTP 504. The exact xz URL now tries the [official content address](https://snapshot.debian.org/file/c9d85a145fcc34817defe65c818ded141ea2c95f), then its unchanged original URL. One complete HTTP 200 content download matched the retained 4,424-byte cache and same-URL index fact (SHA256 `fe771d58d4af39dbb94142d6f3ce578d340c6b1364c172d9e87f2287bdc4994b`) in an accepted earlier native artifact. This is not a failed-run lock or signed Release verification: the selected Distroless resolver does not verify Release/InRelease, and supplies fact integrity only when available. That original exception left other suites, architectures, dates and index formats unchanged; the two later exact index additions are documented below. All generic index exclusions remain. Configured-fetch and current consumer acceptance are pending. No package was generated or executed.

[PR163 native FRR](https://github.com/securely1g/sonic-buildimage/actions/runs/42127461594/job/127595197367) executed 538 processes before its build-tool input `libgcrypt20_1.11.0-7+deb13u1_amd64.deb` failed with dated security Snapshot HTTP 503. Only that exact URL now tries the official Debian security CDN first and retains its original Snapshot fallback. One complete CDN HTTP 200 download matched the accepted earlier generated lock and retained package-index record: 843,104 bytes, SHA256 `f0eb41f8cb40896e0822e9ab65611e8383c12b721c76c54764f744abb4a8c247`. The current failure URL and unchanged selected APT inputs bind this identity; no failed-run generated lock was retrieved. Other dates, versions, architectures and packages retain their previous routing. Configured-fetch and current consumer acceptance are pending. No package was generated or executed.

[PR196 Framework AMD64 analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42127542459/job/127595462448) failed while resolving `libcap-dev_2.75-10+deb13u1+b1_arm64.deb`: the pool returned HTTP 404 and dated Snapshot returned HTTP 503. Its exact URL now tries the [verified official content address](https://snapshot.debian.org/file/a5c6a45aae0d443be8f13ebc6eddfb3e83e23b55) before the unchanged CDN/original fallbacks. One complete HTTP 200 response matched the retained cache and accepted earlier generated lock: 470,800 bytes, SHA256 `f1c0687bb0f6ad192b9cbe64429fc76029ce2a11939b155051139caf1683b447`. The exact current URL and byte-identical selected iproute2 recipe bind that historical record; no failed-run generated lock is claimed. This ARM64 input is selected during AMD64 analysis, not an ARM execution request. Package identity, integrity checks and unrelated routes are unchanged. Configured-fetch and consumer acceptance remain pending; no package was generated or executed.

[PR163's AMD64 archive job](https://github.com/securely1g/sonic-buildimage/actions/runs/42127461726/job/127595197988) later failed in Sysmgr source-image dependency analysis on `rsyslog_8.2504.0-1_amd64.deb`, with pool HTTP 404 and dated Snapshot HTTP 503. This is distinct from the earlier `rsyslog-relp` input. Its exact dated URL now tries the [verified official content address](https://snapshot.debian.org/file/3745d404bae6227eb2142ce4aa8baeb8b0cad14d), retaining the existing CDN and original Snapshot fallbacks. One complete official HTTP 200 download matches the current checked-in base-image lock and retained cache: 758,296 bytes, SHA256 `815203243b9eb17c72c0229fe26afb525542b867719ab36413ab8e514159a26b`. Package versions, checksums and source-image targets are unchanged; configured-fetch and consumer acceptance remain pending. No package was generated or executed.

[PR151's AMD64 archive validation](https://github.com/securely1g/sonic-buildimage/actions/runs/42121419709/job/127574455212) built the Orchagent variants and validated installed sources before its source-file dependency query failed on `libkadm5clnt-mit12_1.21.3-5+deb13u1_armhf.deb` with dated security Snapshot HTTP 504. The same query warned that `krb5-multidev`, `libkrb5-3` and `libgssapi-krb5-2` at that version and architecture returned HTTP 503, timed out, or returned HTTP 504. Only these four exact dated URLs gain official content alternatives, each retaining its original Snapshot fallback. One complete HTTP 200 content response per input matches the accepted earlier generated lock and full cache bytes. The current source-owned libteam dependency recipe has the same `apt.install` declaration as the accepted recipe; this binds the historical lock without claiming a retrieved failed-run lock or current use of the old registry libteam entry.

| Package (ARMHF, `1.21.3-5+deb13u1`) | Observed role | Bytes | SHA256 |
| --- | --- | ---: | --- |
| [libkadm5clnt-mit12](https://snapshot.debian.org/file/79a0f5873bc04d427cd972471105e1fcf64dd089) | Fatal fetch | 37,844 | `166c0b71c91257d725d624ac8bbf345104dce0038451fb6104a0e7eea89278bb` |
| [krb5-multidev](https://snapshot.debian.org/file/20d0dda5ff37855ff607673ee54c7c9608bd9d7b) | Sibling warning | 126,412 | `1e9476397e2ee8a749286e60d42fe08abfa0cc4b59703567821fff3d40b66559` |
| [libkrb5-3](https://snapshot.debian.org/file/c05801948acf5d6932a3ba59a52413725b1ead42) | Sibling warning | 284,480 | `988151350dfb736c7bb461ffb24bf136aeae72842838270f44d482b7f70d8167` |
| [libgssapi-krb5-2](https://snapshot.debian.org/file/b52a9657c1c4c021218236cd2c58c2db7b85d55c) | Sibling warning | 115,712 | `df4ca163a4d682caac2e1fca14d83b6fac3899829856f62fe81f45dc578c7c70` |

Package identities and hashes are unchanged. ARMHF input resolution during the AMD64 query does not execute ARM code. Configured-fetch and consumer acceptance remain pending; no package was generated or executed.

Their rewrites match the exact timestamp, version, and architecture. Local HTTP
fixtures exercise the added candidates, fallback to the original paths, and
rejection of corrupt mirror bytes. Cold Bazel fetches verify the packages
selected by hosted ARM jobs and the cross-build survey against their original
locked hashes and sizes. These validation inputs and their listed locked sibling architectures also
have a content-only fetch test, so an available original URL cannot mask an unusable alternative.
Neither architecture's package binaries are executed by these fetch tests.

Other timestamped `snapshot.debian.org/archive/debian/.../pool/*.deb` downloads
try the identical pool path on Debian's official `deb.debian.org/debian/` CDN
first, then retain the exact timestamped snapshot URL as fallback. This avoids
transient snapshot HTTP 503 failures for package versions still present in the
current pool; older packages absent from the CDN continue through the snapshot.
Binary-package inputs on `snapshot-cloudflare.debian.org` try the identical CDN
pool path, then the identical timestamp/path on `snapshot.debian.org`, then the
original Cloudflare snapshot URL. The native AMD64 and ARM64 BusyBox 1.36.1-6
packages declared by `rules_coreutils@1.0.1` retain all three candidates, with
cold-fetch regressions checking both original SHA256 hashes without executing
either package.
The locked filename, version and SHA256 remain unchanged. The generic rules do
not rewrite indexes, metadata, source archives, or `debian-security`; only the
exact security-package exceptions listed above are added. The cold-fetch
regression checks `libsframe1_2.44-3_amd64.deb` against
its generated APT lock's SHA256
`38f625dfdc582717029ac3a3e97c51d994ec2e7a0e9b230c6b44e40d1276311f`.

Repository downloads allow 12 HTTP connection attempts with a nominal 10-second
retry-delay cap and at most four parallel downloads per Bazel process. These flags
apply to both architectures, repository-dependent commands and Rust preparation;
the cold-fetch regressions use the same policy. This allows transient HTTP
503/504 responses to recover without changing package inputs or retrying tests.

BCR `pigz@2.8.bcr.2` is used by build-infra's reproducible gzip tool when packaging
WPA's debug TAR. Its original URL now serves different bytes; a clean
[WPA registry build](https://github.com/securely1g/sonic-bazel-registry/actions/runs/41587703074/job/125760920377)
fails its BCR checksum before compiling any source.

The MacPorts mirror retains the original archive with SHA256
`eb872b4f0e1f0ebe59c9f7bd8c506c4204893ba6a8492de31df416f0d5170fd0`.
Bazel still verifies BCR's unchanged integrity and applies its unchanged patches.
No source/version override, custom module, or disabled integrity check is involved.

This config applies automatically in this registry's validation runner. It does
not change how standalone consumers download dependencies. Until BCR's upstream
source location is repaired, standalone callers can opt in using an absolute
path to a checkout of this config:

```sh
bazel build --experimental_downloader_config=/path/to/sonic-bazel-registry/ci/source_mirrors.cfg //your:target
```

The real Bazel runner tests fetch the five ARM archives, gawk, BCR's pigz and the
locked Debian package into new, empty repository caches without a distdir,
checking original archive hashes and
fetched MODULE files. Local HTTP fixtures verify candidate order, fallback after
HTTP errors and checksum mismatches, and rejection when every candidate has the
wrong bytes. These are repository fetches; they execute no compilation or package
actions.

## Additional historical Debian payloads

PR228 retains the verified content alternatives for 17 exact historical package
URLs not already covered by the maintained routing. The prior 19 content IDs
remain available; main already supplies the same `libaudit-dev` and `uuid-dev`
IDs. Each exact content URL is tried before the maintained pool/original
fallbacks. The two security-header exceptions retain only their exact official
security-pool and original URLs; they do not add generic security routing.
All 35 maintained rules and their ordering remain unchanged. The superseded
broad Snapshot-to-Cloudflare/index rewrite is not restored.

The [earlier 228 documentation](https://github.com/securely1g/sonic-bazel-registry/blob/a743fea46c18cf5d45e8895f3a823ee148a55a3e/ci/README.md#pinned-debian-package-downloads)
retains the original package hashes, observed failures and provenance. Those
cases cover declared tools and Libteam, FRR, MACsec and source-image analysis.
The existing ARM64 `libc6` record is read during AMD64 multiarch sysroot analysis;
retaining its route does not request ARM execution or change package selection.

The latest [FRR native failure](https://github.com/securely1g/sonic-buildimage/actions/runs/42051339153/job/127327932746)
and [OCI Sysmgr analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42051339203/job/127327935067)
needed `libpython3.13-stdlib_3.13.5-2+deb13u4_amd64.deb`; [Eventd](https://github.com/securely1g/sonic-buildimage/actions/runs/42051339451/job/127327933410)
needed `perl_5.40.1-6_amd64.deb`. One official content GET per payload returned
HTTP 200: Python 1,957,100 bytes and Perl 267,336 bytes, matching the accepted
`c589d2e5` lock and local cache. The failed `f750ee5c` retains those module and
download inputs; its generated lock was not used. Config comments retain the
full authoritative SHA256; the URL's SHA1 only locates the file. OCI's earlier
archive build and 12 tests had passed. Separate Cloudflare probes timed out
from this workspace, without proving a permanent mirror failure.

The exact owned `codex/registry-debian-pool-transport` branch retains normal
publication-policy planning and both runner/fetch suites. Its existing narrow
branch/repository/path guard empties both native module matrices. Other branches
and unexpected changes retain their normal checks or fail the guard. This
remains a Draft readiness limitation. The successful 6e305 runner/fetch evidence
is historical; refreshed-head CI and consumer pin adoption remain separate.

FRR AMD64 analysis also needs the unchanged
`libperl5.40_5.40.1-6_amd64.deb` and `uuid-dev_2.41-5_arm64.deb` inputs.
Their pool and dated Snapshot URLs returned HTTP 404. Add their verified
content URLs before the existing pool/original fallbacks: retained once-only
GETs matched the accepted lock's SHA256 and sizes (4,341,332 and 49,472 bytes).
UUID is imported during AMD64 analysis; this is not ARM execution. Existing
scope tests distinguish UUID architectures, and the existing cold-fetch suite
includes both package identities. Configured-fetch and consumer acceptance
of this reconciled head remain pending.

The existing `libssl3t64` AMD64 route and its sibling-architecture tests remain
unchanged. Its content ID, locked SHA256 and 2,447,924-byte size match the
retained successful filename-suffixed redirect. No second SSL rule or download
is added; configured acceptance of the preserved bare content URL remains
pending. Published review config `264002ba` and all consumer pins stay intact.

Eventd AMD64 tests also import the exact private
`redis-server_8.0.2-3+deb13u2_amd64.deb` input. Its security pool and dated
Snapshot URLs returned HTTP 404 before any native action. The exact security
Snapshot exception now tries the official content ID, then the original URL;
one retained GET matched the locked SHA256 and 66,576-byte size. The existing
scope and cold-fetch fixtures include this input; generic security and index
URLs remain excluded. New-head configured fetch and Eventd acceptance remain
pending.

The inherited Python AMD64 development-package route is unchanged. Its
`3cb20569` content ID matches retained cache bytes: 5,275,756 bytes with the
selected `libpython3.13-dev_3.13.5-2+deb13u4_amd64.deb` SHA256. This is byte
identity evidence, not a new HTTP availability result; no duplicate route or
package download was needed.

The shared SWSS image [source-base AMD64 job](https://github.com/securely1g/sonic-buildimage/actions/runs/42104208737/job/127514624945)
failed on `libkrb5-dev_1.21.3-5+deb13u1_amd64.deb` with Snapshot HTTP 503.
Its [native AMD64 job](https://github.com/securely1g/sonic-buildimage/actions/runs/42104209054/job/127514625948)
failed on `libpcre2-8-0_10.46-1~deb13u1_amd64.deb` after pool HTTP 404 and
Snapshot HTTP 503; earlier warnings also identified `libpcre2-dev` at the same
version for AMD64, ARM64 and ARMHF. Exact content routes cover these five
inputs, retaining the original URL and existing pool fallbacks. All five
cached payloads match the retained accepted lock's SHA256 and size. One direct
official content GET each also matched Krb5 (16,204 bytes) and PCRE runtime
(298,536 bytes); official `binfiles` metadata binds the three PCRE development
content IDs to the cached bytes. The current failed URLs and unchanged selected
inputs match that lock; a current failed-run lock was not retrieved. These
routes do not change package selection or execute ARM workloads. Current
configured-fetch and consumer acceptance remain pending.

The [FRR source-base AMD64 job at `a4166f88`](https://github.com/securely1g/sonic-buildimage/actions/runs/42105759505/job/127520018713)
failed its first query on `rsyslog-relp_8.2504.0-1_amd64.deb`: the official
pool returned HTTP 404 and the dated Snapshot URL returned HTTP 503. One exact
content route now precedes the existing pool and original URL fallbacks. A
retained official GET returned 316,252 bytes matching the checked-in
`docker-base-trixie/bazel/apt.lock.json` record and the complete cached payload's
SHA256. The package version and hash remain unchanged; the content URL's SHA1
is only a locator. Existing parameterized scope and configured-fetch tests
include this identity. New configured-fetch and consumer CI acceptance remain
pending, and this route does not claim to repair other Snapshot outages.

The [SWSS AMD64 archive job](https://github.com/securely1g/sonic-buildimage/actions/runs/42104208903/job/127514637058)
then failed on `libjq1_1.7.1-6+deb13u2_amd64.deb` after earlier phases completed
5,780 processes. Its later query reported zero processes. The same log and
[FRR image AMD64 job](https://github.com/securely1g/sonic-buildimage/actions/runs/42104634546/job/127516099742)
identified `ss-dev_2.0-1.47.2-3+b11_armhf.deb`; each input's pool returned
HTTP 404 and dated Snapshot returned HTTP 503. Two exact content routes now
precede their existing pool/original fallbacks. One retained official GET each
matched the locked/cache SHA256 and size: JQ 164,336 bytes and ss-dev 34,996 bytes.
JQ also matches the current checked-in source-base APT lock. The ss-dev record
comes from retained accepted generated-lock evidence with the exact current
failure URL, not a newly retrieved failed-run lock. These are declared inputs
during AMD64 analysis; no ARM execution or package-version change is added.
Configured-fetch and native acceptance remain pending. Separate libcap and
SQLite backend failures remain unresolved.

The SWSS AMD64 archive [job at `44c6f256`](https://github.com/securely1g/sonic-buildimage/actions/runs/42115421331/job/127553658046)
failed Python-target analysis on `libexpat1-dev_2.7.1-2_amd64.deb`: the
official pool returned HTTP 404 and the dated Snapshot returned HTTP 504.
One exact content route now precedes the unchanged CDN and original Snapshot
fallbacks. A retained official GET returned 160,568 bytes matching the current
checked-in `platform/vs/docker-syncd-vs/bazel/apt.lock.json` record and complete
cache payload (SHA256 `ac1e7f8ad81578b61bc7c54c725ec639b06684e560766eac278490a1b2064372`).
The content SHA1 is only a locator; package selection, integrity, runtime
libexpat routes and other architectures are unchanged. The existing exact-input
tuple checks cover this route; configured-fetch and consumer acceptance remain
pending. No package generation or execution was needed.

The same AMD64 analysis log also warned about
`libkrb5support0_1.21.3-5+deb13u1_amd64.deb` and
`comerr-dev_2.1-1.47.2-3+b11_arm64.deb`; their Snapshot requests returned
HTTP 504, and the comerr pool request returned HTTP 404. These were warnings;
libexpat-dev remained the final fatal input. Two exact content routes retain
the original URL fallback, with the existing generic CDN fallback for comerr.
Retained official HTTP 200 responses match complete cache bytes and locked
SHA256/size: Krb5 support 33,124 bytes, comerr development 56,944 bytes.
Krb5 support binds to the current checked-in syncd APT lock. Comerr binds to
the accepted `e84f45e6` generated lock in 22 dependency sets and the exact
current warning URL; no newly retrieved failed-run generated lock is claimed.
The ARM64 package is an input of AMD64 analysis, not an ARM execution request.
Existing exact-input tuple checks cover both; package selection and checksums
are unchanged, and configured-fetch/consumer acceptance remain pending.

[PR151 Rust analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42139057262/job/127634451598)
stopped on `libc-dev-bin_2.41-12+deb13u3_amd64.deb`, and its
[source-base analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42139057197/job/127634451053)
stopped on `libaudit-dev_4.0.2-2+b2_armhf.deb`. Both pool URLs returned HTTP 404
and dated Snapshot URLs returned HTTP 503 before any action processes ran.
Two exact content routes now precede the existing pool/original fallbacks.
One official GET per input matched the accepted generated-lock SHA256, size
and complete retained cache bytes: libc development tools 59,836 bytes and
audit development files 84,264 bytes. The current infra recipe and FIPS
OpenSSH dependency selection bind those inputs; no failed-run lock or whole
graph equivalence is claimed. The ARMHF input was requested during AMD64
analysis, not ARM execution. Package versions and hashes remain unchanged;
the content SHA1 is only a locator.
Configured-fetch and native acceptance are pending; no package was executed.

The same source-base log warned that
`comerr-dev_2.1-1.47.2-3+b11_armhf.deb` returned pool HTTP 404 and dated
Snapshot HTTP 503. It was not the first fatal input. Its one official content
GET matched all 56,184 bytes and the accepted lock/cache SHA256. The identical
current OpenSSH dependency selection reaches this input through the retained
`libkrb5-dev` closure. One exact route retains its existing pool/original
fallbacks. Other warnings remain outside this change.

[PR196 MUX AMD64 analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42146497352/job/127659127798)
failed on `libaom3_3.12.1-1_amd64.deb` in the Graphviz build-tool dependency
closure. Its exact dated URL now tries verified official content before the
unchanged pool and original Snapshot fallbacks. A first bounded content request
timed out; a separately authorized second request returned HTTP 200 and matched
all 1,871,136 bytes, the accepted lock SHA256 and full retained cache bytes.
The current build-tool/source-list declarations and constants match the accepted
record; no failed-run lock, direct Graphviz dependency edge or whole-graph
equivalence is claimed. The content SHA1 is only a locator, and the locked
SHA256 remains unchanged. Existing tuple controls cover neighboring versions,
architectures, dates and paths. Configured-fetch and consumer acceptance remain
pending; no package was generated or executed.

[PR196 Eventd](https://github.com/securely1g/sonic-buildimage/actions/runs/42146497593/job/127659129066)
and [MACsec AMD64 analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42146497396/job/127659127961)
also stopped on
`curl_8.14.1-2+deb13u4_amd64.deb`. Two requests to its bare content URL
returned HTTP 503, and the alternate official Snapshot host failed during TLS.
Official file metadata identified a July 1 dated alias; one request to that
alias followed a single redirect to the named content URL and returned all
269,904 bytes matching the current checked-in lock and cache SHA256. Only the
original July 27 URL gains that verified final content URL before its existing
CDN/original fallbacks. The optional encoded filename is part of the content
URL; the SHA1 locator remains `7ba41bdcd2ca506a7d43c424db9cde0662a868ca`.
Package version, checksum and architecture selection are unchanged. The existing
tuple tests cover this URL spelling; configured-fetch and consumer acceptance
remain pending.

[PR196's automatic native ARM64 job](https://github.com/securely1g/sonic-buildimage/actions/runs/42146497565/job/127659129030)
also failed on the declared `gzip_1.13-1_arm64.deb` build tool. One official
content response matched all 135,008 bytes and the accepted lock/cache SHA256.
The selected build-tool/source declarations bind that historical record without
claiming a failed-run lock or whole-graph equivalence. One exact dated route
retains the existing CDN/original fallbacks; the independently verified ARM64
sibling is reflected in the existing AMD64 route test. No manual ARM job or
package execution was requested.

[PR196 gNMI AMD64 analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42146497362/job/127659128419)
could not retrieve all four formats of the dated trixie-updates ARMHF index.
This is the only observed Debian group consistent with the final abbreviated
failure; the separately observed complete trixie-security AMD64 index failure
is a possible additional blocker. The resolver starts downloads concurrently,
so completion order alone does not identify the fatal group. Only these two
exact `Packages.xz` URLs gain content/original alternatives. Each first content
request returned HTTP 503; each separately authorized second request returned
HTTP 200 matching accepted same-URL facts and complete cache bytes (4,408 and
226,940 bytes). The selected resolver and input URLs bind the retained records;
no failed-run facts or signed Release/InRelease verification is claimed.
Existing ARM64 routing and generic index exclusions remain; other dates,
suites, architectures, formats and Contents/Release paths are unchanged.
Configured-fetch and consumer acceptance for these new routes remain pending.

[PR195's existing automatic native ARM64 analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42149240794/job/127668133152)
stopped on
`util-linux_2.41-5_arm64.deb`. One official content response matched all
1,191,312 bytes and the accepted lock/cache SHA256 under the unchanged selected
build-tool declarations. Its exact dated URL now retains content, CDN and
original Snapshot in that order. The same failed query also included gzip's
already verified ARM64 input. These are static findings from an automatic job;
no manual ARM validation or package execution was requested.

That same query warned that `tzdata_2026b-0+deb13u1_all.deb` failed at both
pool and Snapshot URLs, and the selected security Snapshot for
`libk5crypto3_1.21.3-5+deb13u1_arm64.deb` returned HTTP 503. These were warnings,
not the first fatal input. One official content GET per package matched all
264,316 and 81,416 bytes respectively, the accepted lock and retained cache
SHA256 under the same selected build-tool inputs. Their exact URLs gain content
alternatives while retaining the existing fallbacks; the security input keeps
its exact original Snapshot URL. Other pool-only warnings are not broadened
into new routes. Configured-fetch and consumer acceptance remain pending.

[PR195's AMD64 archive analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42149240699/job/127668133187)
subsequently stopped on the security input
`libkrb5-3_1.21.3-5+deb13u1_amd64.deb`; the same query warned that
`libpcre2-32-0_10.46-1~deb13u1_amd64.deb` failed at both pool and Snapshot
locations. Only libkrb5 was the final fatal input. One official content GET
per package matched all 326,056 and 268,056 bytes respectively, the selected
lock records and full cache SHA256. Each exact URL gains its verified content
alternative; the security input retains its original Snapshot fallback, and
PCRE retains its CDN/original fallbacks. Current checked-in base-lock records
corroborate the historical generated APT identity. No package version or source
selection changes, package execution or native acceptance are claimed.

[PR195's existing AMD64 native libteam/SWSS retry](https://github.com/securely1g/sonic-buildimage/actions/runs/42149240794/job/127674102673)
failed during initial analysis because the Graphviz build-tool closure could
not obtain `libgd3_2.3.3-13_amd64.deb`: the pool returned HTTP 404 and the
dated Snapshot returned HTTP 503. Seven internal processes were reported;
this failure does not establish native source compilation. One exact dated
route now tries the [verified official content URL](https://snapshot.debian.org/file/4c4f480af52f60a63e0b8219b4ec8f2fc31b8bd3)
before the unchanged CDN/original fallbacks. Its sole complete HTTP 200 response
matched all 126,224 bytes, SHA256
`79ba1a3ceb098236c7fca7d896964eb478b0c3f368d5ec4fd2c1713788033af8`,
and the retained cache. The current selected infra entry matches the accepted
historical lock registration; no failed-run generated lock or complete current
graph acceptance is claimed. Package versions, checksums, source recipes and
unrelated routes are unchanged. Configured-fetch and consumer acceptance remain
pending; no package was generated or executed.

[PR196's AMD64 archive analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42146497362/job/127659128395)
also stopped on `libaudit-dev_4.0.2-2+b2_arm64.deb` while resolving imported
OpenSSH metadata. The same query recorded exhausted fallbacks for
`libsmartcols1_2.41-5_amd64.deb` and a security Snapshot warning for
`libssh2-1t64_1.11.1-1+deb13u1_amd64.deb`; these warnings are not the first
fatal error. Three exact official content alternatives now preserve those
locked inputs. Each complete HTTP 200 response matched its selected SHA256,
size and retained cache. The security rule retains its exact original dated
URL, without broadening the generic CDN rule. Current checked-in locks and
matching selected FIPS/infra declarations bind the historical generated-lock
records; this is not a retrieved failed-run lock or full graph acceptance.
No manual ARM execution was used. Configured-fetch and consumer acceptance
for these four new input routes remain pending.

[PR196's existing automatic Eventd ARM64 job](https://github.com/securely1g/sonic-buildimage/actions/runs/42156655260/job/127692301423)
failed during dependency analysis when the dated security Snapshot could not
serve `krb5-multidev_1.21.3-5+deb13u1_arm64.deb`. Its exact route now tries
[verified official content](https://snapshot.debian.org/file/a7f775b5c78d9d5e769349d980b05b9f13e891d2) before the same original dated URL.
The sole HTTP 200 response matched all 126,404 bytes, SHA256
`9f5d65a069269b0960418f9d5a3110158234a1efbe9a9feb3650c57422fe41ef`, and the complete retained cache.
The selected current infra APT declaration, source list and architectures match
the accepted historical lock inputs for this tuple; no failed-run generated
lock or full current graph equivalence is claimed. All earlier ordered rules
remain unchanged, including the separate ARMHF Kerberos route. Package versions,
required hashes, source recipes and module files are unchanged. No manual ARM
execution or package generation was needed; configured-fetch and consumer
acceptance for this addition remain pending.

## Exact libsodium input for the Orchagent source-closure query

The [engine archive job at `efea4965`](https://github.com/securely1g/sonic-buildimage/actions/runs/42156655356/job/127692302891)
failed its post-build Orchagent declared-source query when the locked
`libsodium23_1.0.18-1+deb13u1_armhf.deb` security URL returned HTTP 503.
The query already loaded the selected downloader through the common rc flag;
that configuration had no exact rule for this security input.

Only that exact original URL now tries the official content address
`https://snapshot.debian.org/file/60d6945b3aefe2f3abc15790ccddff1ade45376d`
before its original fallback. The complete official response matched all
138,788 retained locked/cache bytes and SHA256
`239ef2d400974ae787c098aadef7c3bc2c81339c36159705010cad6d5e1ed3e3`.
Current source declarations bind this tuple to the accepted generated lock;
no failed-run lock or full current graph equivalence is claimed. The SHA1
locates content; the unchanged SHA256 remains the package integrity check.
Existing ordered routes, package versions, source recipes and module files
remain unchanged. Configured-fetch and consumer acceptance remain pending.

## Exact libc6 ARMHF input for SWSS native analysis

The [SWSS AMD64 analysis job at `ff0f5881`](https://github.com/securely1g/sonic-buildimage/actions/runs/42164696960/job/127730414526)
failed while resolving `libc6_2.41-12+deb13u3_armhf.deb` for the declared
multiarch sysroot. Its official pool and dated Snapshot fallbacks failed.
Two separately recorded bare content requests returned HTTP 503 and the
Cloudflare content endpoint was unavailable. No ARM execution was involved.

The exact dated URL now first tries the verified filename-bearing official
content URL, then retains the existing official pool and original fallbacks:
`https://snapshot.debian.org/file/2511d1ea4cdf37ca307cc3336cbc16ff23c323ef/libc6_2.41-12%2Bdeb13u3_armhf.deb`.
That response returned HTTP 200 and matched all 2,249,772 locked/cache bytes
and SHA256 `8aea0a08cefceb212303a738105ed5befc8fe95a32f465345ab5eec305f21d09`.
The filename-bearing form follows the already verified curl route. Its SHA1
locates content; the unchanged SHA256 remains the package integrity check.
Current selected infra declarations bind this tuple to the accepted lock;
no failed-run lock or full graph equivalence is claimed. Package versions,
recipes, other routes and module entries are unchanged. Configured-fetch
and consumer acceptance for this addition remain pending.

## Exact Socat source archive fallback

The [SWSS image source-base workflow at `6ab506bd`](https://github.com/securely1g/sonic-buildimage/actions/runs/42055651322/attempts/2)
failed fetching `socat_1.8.0.2-1.debian.tar.xz` from both declared Snapshot hosts.
Its [selected Socat recipe](https://github.com/securely1g/sonic-bazel-registry/blob/ccd4d6c2a6e3551f40e0d973ef5756006eba7e9d/modules/socat/1.8.0.2.sonic.3/MODULE.bazel)
pins SHA256 `04b361cd91884eda6ca9fe2890ca83a6abe73dd8ce75fe9927b2d8443af36123`.
One official content GET returned the identical 15,148 bytes from
`https://snapshot.debian.org/file/0475522901bd85478b944520b23e01e3f3c7d339`.
The SHA1 path locates the file; the existing repository rule still verifies the
unchanged SHA256 before extracting Debian's patches.

The Debian-patch exception tries only that exact verified content address
before its original URL. It does not match the separate original-source input.

The [MUX AMD64 source-image job at `08d51ffe`](https://github.com/securely1g/sonic-buildimage/actions/runs/42171557668/job/127740336754)
later failed fetching `socat_1.8.0.2.orig.tar.bz2` with dated Snapshot HTTP 503;
the official Debian pool returned HTTP 404. Its selected `socat@1.8.0.2.sonic.6`
recipe and source SRI bind the original archive to SHA256
`adc07a9c2723527cf6568d2fb96559794cf9c254a4bc2edd36f7f3789e9f7625`.
One [filename-bearing official content response](https://snapshot.debian.org/file/5a4a6a0e9819a6279e733c6cffd64ac150df93df/socat_1.8.0.2.orig.tar.bz2)
returned HTTP 200 and matched all 579,370 retained cache bytes. That exact dated
original-source URL now tries the verified content URL before its unchanged
original fallback. The `.tar.bz2` filename is retained because this source rule
infers the extraction type from the URL; no archive type, source version or
integrity changes. The original archive and Debian patches remain distinct.

Pure routing tests check both exceptions and reject other source archives,
indexes, near-miss versions and dates, paths, hosts, queries and fragments.
The separately declared Cloudflare URLs remain unchanged. These GETs prove
byte availability; configured-fetch and new consumer acceptance remain pending.

The [PR196 AMD64 archive job at `08d51ffe`](https://github.com/securely1g/sonic-buildimage/actions/runs/42171557768/job/127740337397)
built and validated Orchagent with 106 ELF/debug pairs and 370 Scapy files,
then a separate source-closure query failed on
`libpcre2-32-0_10.46-1~deb13u1_armhf.deb`: the official pool returned HTTP 404
and the dated Snapshot returned HTTP 503. The query failed before that step's
owner tests ran. Its unchanged selected libyang module requests ARMHF
`libpcre2-dev`, whose accepted generated-lock closure includes this exact PCRE32
package; no current failed-run lock or complete graph equivalence is claimed.

One [official metadata response](https://snapshot.debian.org/mr/file/9eb28eee9a02941c85af546838293851576cdfa7/info)
binds the filename, size and content SHA1. One [filename-bearing content response](https://snapshot.debian.org/file/9eb28eee9a02941c85af546838293851576cdfa7/libpcre2-32-0_10.46-1~deb13u1_armhf.deb)
returned HTTP 200 and matched all 235,052 locked/cache bytes and SHA256
`ab7a0ed7616e15eb569d4df827b6aceb3f6d810959a8970a426614400d92c7e6`.
Only that exact dated URL gains the verified content candidate before the
unchanged official-pool and original Snapshot fallbacks. The existing AMD64
PCRE32 route remains separate. Package versions, integrity checks and all
other routes are unchanged. No package generation or execution was needed;
configured-fetch and consumer acceptance for this successor remain pending.

The [PR195 ARM64 archive job at `314d872c`](https://github.com/securely1g/sonic-buildimage/actions/runs/42182694599/job/127775737269)
failed its initial 24-target Python/startup no-DEB query on
`libexpat1-dev_2.7.1-2_arm64.deb`: the official pool returned HTTP 404
and the dated Snapshot returned HTTP 503, with zero action processes.
The unchanged current infrastructure declaration and registry hashes bind the
accepted generated-lock tuple and retained cache; no failed-run lock or
complete graph equivalence is claimed.

The one official metadata request returned HTTP 504 and did not confirm the
identity. A separately authorized [filename-bearing content response](https://snapshot.debian.org/file/b0fd006c705d3b52a70b6378819d3478dec226f1/libexpat1-dev_2.7.1-2_arm64.deb)
returned HTTP 200 and matched all 144,948 locked/cache bytes and SHA256
`b219482f10e9a0e52474db2a6f239057ea27fea0db0071e3ddb41e8a8a06064c`.
Only this exact dated URL gains that content candidate before the unchanged
official-pool and original Snapshot fallbacks; the prior AMD64 development
route remains separate. No package generation or execution was needed.
Configured-fetch and new consumer acceptance remain pending.

## Kernel build-tool cache downloads

The runner starts each consumer with `--ignore_all_rc_files`, so it explicitly
passes the same download policy as the source repositories:

```text
--remote_download_regex=(^|.*/)tools/build_tools/kernel_runtime_(amd64|arm64)(/.*)?$
```

This applies to build, test and output-query commands for both native
architectures, including checked-in integration test modules. It downloads the
kernel build-tool tree before local actions use its directory symlinks. For
example, sairedis' generated Debian metadata uses those tools; restoring the
cached tree without this policy can leave its Perl `5.40/machine` alias missing.
[The native cache experiment](https://github.com/securely1g/sonic-build-infra/actions/runs/40080628232)
reproduced that failure and verified the targeted flag on AMD64 and ARM64.
Other output trees keep Bazel's normal download policy. Read-only `info` path
queries do not need the flag.

## How CI selects the latest version

Routine CI compares the numeric release, then the SONiC patch revision. For
example, `0.9.4.sonic.10` is newer than `0.9.4.sonic.9`, and `0.9.5.sonic.1`
is newer than both. Existing `-sonic.N` spellings remain supported; the dotted
spelling wins when the release and patch revision match.

For source versions with the same numeric release, the last registration in
`metadata.json` wins. Git hashes do not indicate which commit is newer. Append
new registrations without reordering existing entries. A later append of an
older release cannot displace a higher release: build-infra `0.0.18-95cd3a9...`
is selected ahead of any `0.0.8-...` registration. This is a CI selection rule,
not a change to Bazel's dependency resolution.

Latest selection skips versions listed in `yanked_versions`; a module with all
versions yanked contributes no routine jobs and is reported in the plan log.
Modules with no `presubmit.json` at any version remain outside CI coverage.
For a module already covered by CI, the latest non-yanked version must have a
configuration: planning fails instead of silently testing an older version.

A PR that revises an unreleased `modules/sonic-build-infra/0.0.8-.../` candidate
still tests that exact version. Maintaining a published version's standalone
tests or `presubmit.json` also tests that exact version, even when it is historical.
Disallowed published input changes are rejected before selecting jobs.
If it also changes CI, the plan includes both the edited version and the latest
version, once each. Module metadata changes retain their existing
coverage: an append-only release addition tests the added versions; other
metadata edits test every listed version. Explicit `plan --all` includes every
version with a configuration, including historical or yanked versions, without
replacing one with another.

Latest selection only changes which standalone module jobs run. Each selected
version keeps its declared architectures, targets and `consumer_deps` pins;
older versions remain available to consumers and can still be tested explicitly.
Routine CI does not claim that all historical versions passed.

## Publication policy checks

Before selecting module jobs, the planner checks that each affected module has
at most one version absent from the maintained `main` branch. Published consumer
inputs must remain identical, and metadata must list every version directory.
This also checks inherited candidates when a PR changes only
metadata or documentation; the actual stacked PR base is used only to select
validation jobs.

For supported archive entries, the only mutable entry-relative paths are regular
files at `README.md`, `PATCHES.md`, `docs/**`, `presubmit.json` and `tests/**`.
These may be added, edited or removed, and regular maintenance files may change
their executable bit. All other paths are protected by their Git object type,
mode and contents. This includes `MODULE.bazel`, `source.json` and every file
under `patches/` or `overlay/`, even if its name looks like documentation or a
test. Symlinks and submodules are never maintenance files. Source layouts or
recipe fields not understood by this policy retain whole-entry immutability.

The unchanged source recipe takes precedence over the maintenance allowlist:
the checker protects a local file named by its source fields, including archive
or mirror URLs with that relative path. URL escaping and dot components are
normalized before comparison. This check is intentionally conservative, so an
unrelated fetch URL with the same path suffix also protects the local file.
The informational `docs_url` field is excluded from this reference check;
`source.json` itself remains immutable. The checker does not try to infer that
an unknown file or source layout is safe to change.

Permitted published documentation changes select no module jobs on their own,
so historical entries need no new `presubmit.json` merely to fix their README.
Standalone test or CI-manifest changes select the exact affected version and
must pass its configured native tests. Shared CI changes retain their ordinary
latest-version matrix. No source payload changes or weakened test assertions
are implied by a maintenance exception; ordinary review still applies.

For example, with `libyang-python@3.1.0.sonic.2` on `main`, a parent adding
`.sonic.3` and a child adding `.sonic.4` fail with two unreleased candidates.
After `.sonic.3` reaches `main`, preserving its consumer inputs and adding
`.sonic.4` passes. Updating `.sonic.3`'s standalone tests instead uses its existing
version. Unchanged historical releases do not require new CI manifests.

For PRs and manual runs, the workflow explicitly fetches the public maintained
repository's `main` and records its SHA in `plan.log`. It does not trust a fork's
branch or treat a stacked PR base as publication. For pushes to `main`, the
publication baseline is the event's **pre-push** `before` SHA; using current
`main` would compare the push against itself. Pushes also pass `--push` to
compare directly against that baseline, detecting non-fast-forward rollbacks
that remove published entries. Missing or unavailable baselines
fail planning, including in `--latest` and `--all` modes.

Affected modules are those changed from the common ancestor of that publication
baseline and the checked-out head. Releases in unrelated modules after a branch
fork do not count as deletions. If a touched module has since published a new
version, rebase to retain its published entries. Protected file comparisons
include contents, modes, additions, deletions and type changes.

CI sees the checked-out stack, not independent open registry PRs or downstream
repositories. Authors must also audit those PRs and update affected consumer
versions, registry revisions, overrides, and lockfiles when consolidating a
candidate. This policy does not change native module validation coverage.

## Module configuration

Add `modules/<name>/<version>/presubmit.json` with the module's registry change.
Each module registration or update belongs in its own PR, including its
configuration and tests. The initial example is
[`libyang 3.12.2.sonic.1`](../modules/libyang/3.12.2.sonic.1/presubmit.json).
The initial validator supports HTTPS source archives with integrity hashes and
optional patches and overlays. Other registry source types need explicit runner
support before onboarding.

The configuration declares:

- `architectures`: target architectures to validate, currently `amd64` and/or
  `arm64`. Execution remains native unless an exact ARM version is selected for
  staged cross validation.
- `consumer_deps`: additional direct dependencies required by the test consumer,
  each with `name`, an exact `version` to test, and optional `repo_name`. CI pins
  every entry to its declared version using `single_version_override`; no
  separate pin flag or override map is needed. Use the module's `name` for
  selection; `repo_name` only controls its apparent repository name in targets.
- `platforms`: an explicit Bazel target platform label for each architecture.
- `host_platforms` (optional): an explicit Bazel host platform label for every
  architecture in `architectures`. This selects the default execution platform
  used to compile tools such as a source-built P4 compiler. A Trixie target
  platform alone does not select the Trixie toolchain for execution dependencies.
  For those consumers, map each architecture to its native Trixie platform,
  matching `platforms`. The runner passes the choice to build, test and info
  commands and records `platform` and `host_platform` in `validation.json`.
  Omitting the map preserves Bazel's existing host-platform default and records
  `host_platform: null`; no host flag is added to other modules.
- `build_targets`: required output labels, including runtime and matching debug
  packages where the module provides them.
- `test_targets`: explicit consumer and package test labels.
- `integration_test_module` (optional): an entry-relative directory containing a
  separate test module, for example `tests/integration`. CI copies its ordinary
  `MODULE.bazel`, `BUILD.bazel`, tests and fixtures into the fresh consumer. The
  test module must directly select the tested module's exact name and version;
  it cannot use source overrides or include other MODULE files. Keep
  `consumer_deps` empty and omit the generated Go/Rust options in this mode:
  the checked-in test module owns its dependencies and toolchains. Explicit
  root targets such as `//:archive_contract_test` are then allowed alongside
  `@<module>//...` targets. Omitting this field keeps the generated consumer.
- `test_runtime_preparation` (optional): reuse the tested source's Python helper
  to prepare runtime libraries in the disposable native test container. Set
  `script` to its path relative to the fetched source and `sha256` to the exact
  file digest. For example, Common's C++ and Rust tests need `libhiredis.so.1.1.0`
  at execution time; its existing helper installs missing runtime packages from
  the resolved Debian snapshot without changing the compiler or built library.
  No module opts in implicitly, and the registration must review the helper's
  package selection and installation behavior together with its checksum.
- `generated_module_overlay` (optional): set to `true` to derive
  `overlay/MODULE.bazel` from the maintained registry `MODULE.bazel`, as described
  below. Any other value is rejected. Omit the field for existing entries that
  maintain their source module through other overlays or patches.
- `go_sdk` (optional): select the consuming root's Go SDK with an exact stable
  version, for example `{"version": "1.25.0"}`. Declare `rules_go` in
  `consumer_deps` unless it is the tested module. The runner uses that
  dependency's apparent `repo_name` to call its `go_sdk` extension and download
  the selected version. This supplies the ordinary root SDK declaration that a
  dependency's `dev_dependency` extension cannot provide. Omitting this field
  preserves rules_go's default SDK selection. The generated declaration and
  `validation.json` record the choice; build and test coverage is unchanged.
- `build_flags` (optional): module-qualified Starlark settings applied to both
  builds and tests, for example
  `--@sonic-swss-common//tools/bazel:yang_modules=False`. Each setting must belong to
  the module under test and include its value. Native Bazel options, duplicate
  settings, and options that redirect registries or override test execution are
  rejected. The selected flags are retained in `validation.json`.
- `rust_toolchain` (optional): declare the consuming root's Rust toolchain with
  an exact stable version, for example `{"version": "1.90.0"}`. Declare `rules_rs`
  in `consumer_deps` unless it is the tested module. The runner calls its
  reexported `rust` extension using the declared apparent repository name and
  registers the pinned toolchain for native AMD64 and ARM64. This supplies the
  root declaration required by `rules_rs` 0.1.0 when testing a Rust module as a
  dependency, matching Common and SWSS. Omitting it preserves other consumers.
  The generated declaration and `validation.json` retain the selection.
  Set optional boolean `mangled_allocator_libraries` to `true` for Rust targets
  linked by the C++ toolchain with the allocator shim used by Common and SWSS.
  Set optional boolean `bindgen` to `true` when the consumer needs the
  `rules_rs` binding-generator toolchain. Both default to `false`; the runner
  imports and registers only explicitly requested support.
- `rust_preparation` (optional): prepare one shared Rust dependency module before
  building its targets. Set `module` and its apparent `repo_name` to either the
  tested module or a declared `consumer_deps` entry. Pin `helper_revision` to a
  full `sonic-build-infra` source commit and `helper_sha256` to that revision's
  `tools/rust/prepare.py` file. CI verifies the helper, fetches the declared module
  through this registry, and prepares a private copy. For example, this lets the
  Serde round-trip test use generated Rust dependency metadata without committing
  that metadata in the source archive.

For example, libyang-Python's test environment selects its shared infrastructure
version once in `presubmit.json`:

```json
"consumer_deps": [
  {
    "name": "sonic-build-infra",
    "version": "0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc",
    "repo_name": "sonic_build_infra"
  }
]
```

The runner generates both `bazel_dep` and a version-only `single_version_override`
from that entry. This prevents another dependency from silently selecting a
higher version, including a commit suffix that sorts higher despite belonging
to an older source revision. Arbitrary source, patch, and registry replacements
are not supported. The optional Rust preparation substitutes only a private copy
of the registry-fetched module, with generated dependency metadata. Its module
declaration must still exactly match the registry entry. Dependencies used by
the test environment must actually be fetched;
the runner fails if a declared dependency is missing or its fetched module name
or version differs. An empty `consumer_deps` list adds no pins.

Artifacts retain the generated `consumer.MODULE.bazel`, `MODULE.bazel.lock`,
each fetched dependency's `consumer-dep-<name>.MODULE.bazel`, and `consumer_deps` in
`validation.json`. These pins apply only to this CI test project. Downstream
repositories such as `sonic-swss-common` remain responsible for validating their
own dependency selection and integration builds.

Rust validation also retains the pinned helper, generated override, preparation
log and receipt, and the shared module's Cargo lock, generated Bazel metadata and
source-resolution record. The test consumer has no Cargo workspace of its own;
component-level Cargo compatibility remains covered by source CI.

### Prepare source-owned test runtimes

For a module whose source CI already prepares a locked test runtime, use:

```json
"test_runtime_preparation": {
  "script": "tools/bazel/runtime/prepare.py",
  "sha256": "<SHA256 of that file in the selected source archive>"
}
```

The runner verifies the fetched module and helper before executing it, after
building the selected outputs and before running **all** declared tests. It runs
the original helper from the independent consumer directory with `--lock` set to
that consumer's generated `MODULE.bazel.lock`, `--image-reference` set to the
job's pinned container image, and `--output` set to `test-runtime.json` in the
artifacts directory. The helper must support these arguments; the runner does
not invent package lists or use a lockfile shipped in the source archive.

The helper must use the lock's exact runtime package versions and checksums,
preserve existing container packages and keep project libraries under test out
of the system library directories. It must produce a JSON receipt containing
`architecture`, `image_reference`, `lock_sha256`, and `SONIC_TEST_RUNTIME_ID`,
alongside its selected packages and installed-library hashes. The identity is
the SHA256 of compact, key-sorted JSON for the receipt excluding
`SONIC_TEST_RUNTIME_ID`, `preserved_base_packages` and `lock_sha256`, matching
Common's existing preparation contract. The runner checks that identity and the
receipt's architecture, image and unchanged consumer lock. It passes the identity
as `--test_env=SONIC_TEST_RUNTIME_ID=...` so Bazel's test inputs include the
prepared runtime, without changing production build flags or dropping tests.

Runtime preparation requires root inside a disposable native Debian Trixie
container and an explicit `--test-container-image IMAGE@sha256:DIGEST` argument.
The workflow supplies its actual pinned image; local reproduction must start an
equivalent disposable container and pass that image reference. The runner refuses
host execution and missing container opt-in before starting a build. Merely
passing an image name does not start a container.

Artifacts retain `test-runtime-prepare.py`, `test-runtime.MODULE.bazel.lock`,
`test-runtime-preparation.log`, the helper's `test-runtime.json` receipt and any
adjacent logs, including on failure. `validation.json` records the opt-in and
test environment flag after every declared test passes.

## Maintain one MODULE declaration

For an entry whose source archive needs a MODULE overlay, opt in with
`"generated_module_overlay": true` in its `presubmit.json`. Maintain the complete
module declaration and dependencies in `modules/<name>/<version>/MODULE.bazel`.
Generate the source overlay and its checksum with:

```sh
python3 ci/registry_ci.py sync-module --module NAME --version VERSION
python3 ci/registry_ci.py sync-module --module NAME --version VERSION --check
```

The first command writes `overlay/MODULE.bazel` as a generated-file notice naming
`../MODULE.bazel` and the command, followed by the canonical bytes unchanged. It
also updates only that overlay's integrity field in `source.json`; the rest of
the source manifest remains maintained by hand. A missing overlay is created
after explicit opt-in. Do not edit the generated file or checksum separately.

`--check` writes nothing. Entry validation performs the same check before any
build, so a changed dependency or direct overlay edit fails even if someone
refreshes the overlay checksum manually. Repeated generation leaves matching
files untouched. Entries without this field keep their existing validation.

Bazel writes the canonical registry MODULE after applying source overlays and
patches. The fetched source MODULE must therefore match the canonical registry
MODULE exactly for every entry. The generated overlay is checked separately
before the build. `validation.json` records the canonical, fetched and optional
generated-overlay SHA256 hashes separately, plus `generated_module_overlay`.
`fetched_module_matches_registry` retains its literal byte-equality meaning.

## Native execution and source preservation

Every module uses the shared runner. Before building, it verifies the native
Linux CPU architecture and Debian userspace architecture. It records the exact
registry checkout commit and SHA256 hashes of the selected entry's source files
in `source-validation.json`. The entry must remain unchanged after validation,
including a failed build; mutation fails the job and is recorded in that receipt.
Work directories and artifacts stay outside the maintained entry.

Module-specific checks are ordinary Bazel tests selected in `presubmit.json`.
For example, Distroless's fixture-regeneration test runs its declared helper and
compares the output with the reviewed lock. It uses the same uncached execution
and test-result verification as the archive integration test, with no custom CI
driver or module/version branch in the workflow.

## Resolution and package evidence

The fresh consumer ignores `MODULE.bazel.lock` and uses `--lockfile_mode=update`.
The generated resolution state is copied to artifacts, including after a failed
build when the file exists; it is never committed to the registry. Successful
validation requires that Bazel generated this evidence.

Use explicit labels for required outputs and tests. Wildcard builds can silently
skip targets incompatible with the selected platform. Add tests to the module's
source, registry overlay, or a separate `integration_test_module`. Update the
corresponding overlay integrity hashes when changing overlay files. A successful library build alone does not establish
that downstream consumers can link it or that its runtime package works.

For example, the Distroless locked-import test has its own
`tests/integration/MODULE.bazel` declaring the APT extension, reviewed lock and
two imported package repositories. Its BUILD and Python test verify the archive
contents through that public interface. These are ordinary registry test files;
they need no test-only patch to the dependency's MODULE or source overlay. The
same CI invocation retains the dependency's existing external tests and runs
the root archive test on each configured native architecture.

Integration modules use the same registry, source checksum, fetched-module and
uncached-test checks as generated consumers. They cannot contain symlinks,
hidden configuration, cached lockfiles or Bazel output directories. CI copies
the files before execution, so generated lockfiles and test outputs stay outside
the maintained test directory. The chosen directory is recorded in
`validation.json`, and the staged MODULE and resolution lock remain artifacts.

For libyang, CI builds the runtime and detached-symbol packages, then runs
`libyang_test` and `libyang_package_test`. These cover a dynamic consumer, YANG and
JSON parsing, PCRE2 pattern validation, the SONiC validation flag, extracted
runtime execution, SONAME and symlinks, runtime dependencies, and matching debug
symbols with GDB source-line lookup. This is focused module validation; the
downstream `sonic-swss-common` pipeline remains responsible for its integration
tests.

## Download build outputs

Failed builds and tests retain local action stdout/stderr under
`failed-actions/`, including diagnostics larger than Bazel's console-output
limit. Each `index.json` records the action label, stream, retained path, byte
count and SHA256. Missing files, remote URIs and paths escaping the private work
directory are recorded as collection errors; they are never fetched or copied.
The original build or test failure remains the result.

Open **Actions → Registry CI → a successful run → Artifacts** and download
`registry-ci-<module>-<version>-<architecture>` (`amd64` or `arm64`). Each artifact
contains `registry-ci-evidence.tar`. Extract that first with
`tar -xpf registry-ci-evidence.tar` on a case-sensitive Linux filesystem.
It contains the complete job evidence: logs, manifests, failure diagnostics and
`outputs.json`, mapping required build targets to files under `outputs/` with
SHA256 hashes and sizes. There is no separate all-outputs `outputs.tar` format.

Generated file paths are preserved. Repository files reported without a Bazel
output prefix use their private workspace path under `outputs/source/`. For
example, `external/libc6/control.tar.xz` and `external/netbase/control.tar.xz`
remain separate even though both build-event records are named `control.tar.xz`.
Use the index instead of relying on a configuration
directory name. Directory outputs, such as prepared YANG models and execution
tool bundles, are retained as TARs under `outputs/trees/`. Their index records
have `type: "tree_archive"` and `root` naming the original output path inside the
TAR. Extract the TAR to preserve Unix modes, case-sensitive names, and relative
symlinks within the tree. GitHub's artifact ZIP format cannot faithfully retain
these properties and rejects some valid Linux filenames, including `:` in Perl
manual pages. Links to other outputs inside the build work directory are
materialized so each archive remains usable alone, as are relative links whose
meaning changes when copied into the archive. Links outside the build work
directory are rejected.
Archive ownership and timestamps are normalized; file modes are preserved.
The runner queries Bazel's declared directory outputs under the same build
configuration, since build events expand those directories into individual files.
The query selects `config(label, target)`: if the same target is also a build tool,
its execution configuration must not replace or duplicate the requested output.
Only files within those declared boundaries belong to a tree TAR; adjacent runtime
and debug TAR outputs retain their original bytes. The artifact includes
`declared-output-trees.jsonl` and the genuine build events for verification.

Bazel 8.5.1 can report a Unicode tree member using UTF-8 bytes interpreted as
Latin-1, together with a damaged file URI. For example, registry CI's real
artifact fixture reported `Főtanúsítvány.crt` as `FÅ\x91tanÃºsÃ\xadtvÃ¡ny.crt`
on its AMD64 worker. When that literal basename is absent, the runner tries
one strict Latin-1-to-UTF-8 conversion of the basename. The result must be a
regular file inside the declared tree, with the build event's exact SHA256 and
size; URI-parent, ASCII-name and path-safety checks still apply. Existing
literal names are never reinterpreted, and recovery through a symlink is
rejected. The TAR retains the actual filesystem name and bytes. This does not
change Bazel's locale or repair arbitrary paths. The failed worker's effective
JVM locale was not retained.

The real Bazel collector fixture creates its certificate filename with ASCII
shell octal escapes and checks its exact UTF-8 bytes before collection. Its two
producer actions (target and execution configurations) use
`execution_requirements = {"no-remote-cache": "1"}`. This prevents those actions
from reading or uploading remote cache results while retaining sandboxing,
reuse of existing local action outputs, analysis reuse and caching for the separate tool action and all
module builds. The observed runner command configures a remote cache, not a
remote executor; this action requirement does not disable remote execution.

This isolates collector validation from an unresolved Bazel 8.5.1 remote tree
transport defect. A retained AMD64 run materialized a double-encoded Unicode
filename from cached output and failed the strict filesystem assertion before
the collector ran. The earlier passing run also reported a Unicode runtime
backport, so it is not a controlled cache-only comparison. The fixture keeps
all filesystem, BEP, target-versus-execution configuration and final TAR checks.
Passing it does not establish that production remote tree transport is fixed;
this change neither modifies the Bazel runtime nor changes production caches.

For native libraries, download the runtime and detached-debug packages from the
same module/version/architecture job. These packages come from the same build;
symbols from another run are not guaranteed to match. Extract package archives
to preserve their installed layout and modes. Standalone test launchers in the
artifact are build outputs, not portable installations with all runfiles.

The runner reads the successful build's default output groups, copies the
declared files, and fails if a required target or output is missing. It retains
outputs before running tests, so artifacts from failed jobs may contain packages
that have **not** passed validation. Check the job result and `validation.json`
before using them. Logs and other failure diagnostics remain available.

The two archive levels serve different consumers: `registry-ci-evidence.tar`
transports the complete job through GitHub unchanged, while each indexed directory
TAR is a reusable build output that can be downloaded and extracted separately.
Existing runtime/debug TAR files are not repackaged internally. For example,
`Text::CharWidth.3pm.gz`, `xt_CONNMARK.h`, and `xt_connmark.h` retain their names,
and a directory's executable files and portable relative links remain usable.


`test-results.json` indexes the `test.log` and `test.xml` files declared in each
Bazel test-result event, with its label, configuration, run, shard and attempt.
Files are retained under `test-results/` with SHA256 hashes and sizes. This also
captures tests in transitioned configurations, such as DASH API's Python test,
which are outside the default `bazel-testlogs` directory. The existing
`testlogs/` snapshot remains available for compatibility. A collection error
fails otherwise successful validation; after a build or test failure it is
recorded in `test-results-error.json` without replacing the original failure.
If that receipt cannot be written, the error is printed to stderr and the
original validation failure is still preserved.

## Environment and coverage

Planning, the aggregate check, and AMD64 runner tests and module validation use
self-hosted Debian Trixie Docker runners with the labels `self-hosted`, `Linux`,
`X64`, and `debian-trixie-container`. Register the runners as ephemeral so each
accepts only one job; `sonic-slave-wrk-mgr` must remove the finished container
and replace it with a fresh registered runner after success, failure, or
cancellation. Keep registration credentials in the manager, outside job
containers, and retain runner diagnostics before removing a container.

This staged migration sets `ARM_CROSS_ALL = False`. Only the exact module
versions in `ARM_CROSS_VERSIONS` use native AMD64 cross-compilers and the ARM
runtime executor inside the Trixie runner. Every other ARM version retains its
native GitHub-hosted ARM route, including newer versions of a migrated module.
All original build labels, test labels, sources and dependency pins remain
unchanged. The separate all-ARM survey supplies the acceptance evidence below;
failed or incomplete contracts remain on native ARM while fixes are validated.

Module steps execute directly inside the disposable runner, built from the
pinned Trixie base with compiler and package-test tools preinstalled.
AMD64 does not start a second container or require a Docker daemon. Actions run
as UID 1000; module validation and runtime package preparation use passwordless
`sudo` inside the disposable container. Evidence is archived as root, then only
the resulting TAR is given to the action user, preserving the archived modes.

The manager supplies `SONIC_RUNNER_IMAGE_REFERENCE=sonic-slave-runner@sha256:...`
from the actual derived image's inspected Docker image ID. This is a local
content identity, not a registry pull reference or the upstream base digest.
`validation.json` records the actual local runner identity for native AMD64 and
cross ARM jobs, or the pinned job image for hosted native ARM. Missing local
runner identity fails validation. Runtime preparation receipts
also record the prepared package inventory and library hashes.

The AMD64 image contains the checksum-verified Bazel 8.5.1 binary at
`/usr/local/lib/bazel-8.5.1`. Its `/usr/local/bin/bazel` wrapper explicitly passes
the image's Java CA trust store as a startup argument, including when CI ignores
all bazelrc files. The workflow verifies the binary's checksum again. ARM cross jobs use that same native AMD64 Bazel binary. GitHub
actions are pinned to commit SHAs, checkout does not
persist credentials, and the workflow uses read-only repository permissions.

Local native AMD64 and cross ARM module jobs pass
`--bazel-startup-arg=--host_jvm_args=-Xmx2g` to bound
Bazel's Java heap within each runner's 16 GiB memory limit. The runner accepts
repeated startup arguments, forwards them to build, test, cquery, info and Rust
preparation, and records them in `validation.json`. Hosted native ARM keeps its
default heap.
Repeated `--bazel-build-arg` options reach build, test and output queries.
Local module jobs use `--jobs=1` and `--discard_analysis_cache` to reduce concurrent
compiler memory; Rust preparation receives those settings too. This limits
concurrent Bazel actions; recipes may still request parallel compilation inside
an action. The declared targets and published recipes stay unchanged. A single
local module matrix combines native AMD64 and staged cross ARM jobs, with at most ten running
per workflow run. Hosted native ARM has its own matrix. This is a module limit
per run, not a host-wide limit across runs; planning, native unit tests, the cross
fixture and the aggregate also use workers. Both module groups and both test
suites are required by the aggregate `Registry CI` check. Empty module groups are
accepted only when planning explicitly reports them empty.

Tests receive an explicitly exported empty `HOME`, which Bazel's test setup
replaces with that test's writable `TEST_TMPDIR`. This lets Python and other
subprocesses create user configuration inside the test sandbox; an absent
`HOME` would otherwise fall back to the account's home directory.

`TestRunner` actions prefer `processwrapper-sandbox`. This lets tests hard-link
their declared runfiles into writable temporary directories and set executable
permissions on those private copies. Build actions keep their existing sandbox
strategy. Local or exclusive tests retain the `local` fallback, and real Bazel
regressions cover both paths without changing published tests.

The native helper suite runs on both AMD64 Trixie and GitHub-hosted native ARM64
with the matching checksum-pinned Bazel 8.5.1 binary. Native ARM helper coverage
remains required while any modules retain that route. The separate required
cross fixture tests native execution tools, ARM compilation and ARM runtime
behavior; it does not replace or claim native ARM Bazel execution coverage.
`run_runner_tests.py --suite native` discovers every test file except the ARM
cross-runtime fixture. A separate local job runs `--suite cross` with a 60-minute
bound, both executable prerequisites explicitly set and checked, and failure on
any skipped cross test. A regression verifies that these suites partition full
discovery without overlap or omissions. The native tests build an actual
directory-producing target and its public alias, including both target and execution configurations, then check collection and extraction.
Transport and failure-log tests also cover rejected paths, partial archives,
case-sensitive filenames, Unix modes, empty directories and symlink relocation.

Each job uses a fresh consumer and Bazel output directory. Logs, Bazel build-event files, available test
logs, and validation metadata are retained as workflow artifacts for 14 days,
including when module validation fails. Setup failures can occur before these
files exist and remain visible in the Actions job log.

ARMHF, other operating systems and the complete SONiC image are outside this
matrix. Pull requests validate latest configured versions; the explicit
`all_versions` dispatch also surveys configured historical versions.
Declaring an ARMHF layout in a module does not establish ARMHF build or execution coverage.

## Staged ARM64 cross validation

The shared helper has an explicit cross mode. Each planned row records target
`architecture`, native `execution_architecture`, and a boolean `cross_compile`.
Native callers retain their defaults; cross execution requires both
`--cross-compile` and an absolute executable `--test-executor`, an AMD64 host,
an ARM64 target, and an explicit disposable Debian Trixie container identity.
The reusable workflow selects native Bazel, image, sudo and artifact handling by
execution mode while preserving the target architecture and all original labels.

The temporary `ARM_CROSS_VERSIONS` map selects only complete original contracts
qualified in [the all-ARM survey](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416)
at `88d24c7010a5affd9deb1286e63c5a23e246879c`. The job artifacts bind the exact
source inputs, unchanged selected dependency versions, native execution and ARM
target platforms, produced output identities, and every original uncached test.
A successful build alone is not a module pass. Source-fix probes and diagnostic
replays do not count as survey acceptance. Published-entry immutability remains
enforced; the routing map changes execution placement only.

| Module | Exact version | Build / test labels | Survey evidence |
| --- | --- | --- | --- |
| `gawk` | `5.3.2.sonic.1` | 3 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127198380280) |
| `gazelle` | `0.54.0.sonic.1` | 1 / 3 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127198380420) |
| `libnl3` | `3.7.0.sonic.7` | 5 / 4 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127198380378) |
| `libyang-python` | `3.1.0.sonic.6` | 4 / 3 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127205852291) |
| `protobuf-legacy` | `3.21.12.sonic.2` | 8 / 4 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127218315473) |
| `rules_foreign_cc` | `0.16.0.sonic.1` | 2 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127221268640) |
| `rules_python` | `1.9.0.sonic.1` | 3 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127230792181) |
| `sai` | `1.18.0-sonic.1` | 2 / 3 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127259342573) |
| `socat` | `1.8.0.2.sonic.5` | 4 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127316394685) |
| `sonic-dash-api` | `0.0.5-9b2893e890734a2db0c53a5e5c64b031ec0dcfbd` | 8 / 5 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127363604452) |
| `sonic-linux-kernel` | `0.0.2-34a53faaecd325509e9d8f1016ed0108ab558a23` | 5 / 5 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127391886151) |
| `sonic-rust-deps` | `0.0.4-6d9c70f708d7420e9e2b2cdc906b80cee6b140f1` | 6 / 4 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127417149111) |
| `sonic-yang-mgmt` | `1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d` | 2 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127454762848) |
| `sonic-yang-models` | `1.0.1-b0a9362a7a1b4b5e1b7188c019d256f7c8aaff9f` | 3 / 1 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127456801062) |
| `tar.bzl` | `0.10.5.sonic.2` | 8 / 7 | [Passed](https://github.com/securely1g/sonic-bazel-registry/actions/runs/42013547416/job/127457427548) |

The `linux-kernel` contract validates its declared helpers; it does not build or
boot a kernel image. Passing tests only establish each module's existing
presubmit contract, not broader undeclared functionality. Yang-model package outputs and TAR
regression archives are architecture-neutral; their original target-side runtime
tests remain required, and native execution tools retain their configurations.
The remaining module failures stay visible in the survey and retain native ARM validation here.

The gawk smoke test uses gawk as a native execution tool while the direct gawk
build targets ARM64. Test execution follows the declared Bazel configuration;
the ARM cross fixture independently verifies native execution tools, ARM ELF
outputs and target Python compatibility. No test is replaced by a smaller smoke
test to make a module pass.

Inside a configured disposable runner with `/usr/local/bin/sonic-arm64`, use
fresh work and artifact directories. This command is a local opt-in example,
not a request to execute inside an active registered worker:

```sh
sudo -n /usr/bin/python3 -I -S ci/registry_ci.py run \
  --module libnl3 --version 3.7.0.sonic.7 --architecture arm64 \
  --cross-compile --test-executor /usr/local/bin/sonic-arm64 \
  --test-container-image "$SONIC_RUNNER_IMAGE_REFERENCE" \
  --bazel /usr/local/bin/bazel \
  --bazel-startup-arg=--host_jvm_args=-Xmx2g \
  --bazel-build-arg=--jobs=1 --bazel-build-arg=--discard_analysis_cache \
  --work-dir /tmp/registry-ci-libnl3-cross \
  --artifacts /tmp/registry-ci-libnl3-cross-artifacts
```

Cross mode creates explicit AMD64/Linux/Trixie execution and ARM64/Linux/Trixie
target platforms, retaining other constraints from the declared parents. This
also overrides host-derived aliases that would otherwise select AMD64 output
for an ARM64 request. Published Sonic Trixie platforms keep their toolchains only
when the exact graph-selected `sonic-build-infra` version is in
`cross_toolchain.py`'s verified registration allowlist. Its six immutable entries
declare AMD64 execution, ARM64 targets and Trixie; a familiar platform label or
newer version alone does not establish that capability. All other consumers,
including native-only infra 0.0.6 and SAI's 0.0.13, use a CI-local legacy C++
adapter compatible with the selected `rules_cc`. Both declared platform parents
remain inherited; the adapter's separate distribution constraint is additional.
The adapter uses the native-to-ARM GCC14.2 compiler and Trixie sysroot from
immutable `sonic-build-infra@0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88`.
The provider resolves separately and its JVM stops after preparation. Its
dependencies do not enter the consumer graph. Compiler/sysroot files are declared
action inputs, and the consumer's selected module versions must remain equal
before and after adaptation. Existing integration-module contents are preserved.
Evidence retains both graphs, provider lock and manifests, generated adapter and
platform definitions, declared/effective platform identities, and the selected
infra version and toolchain reuse decision. The registration allowlist is
source-level evidence; actual toolchain and runtime acceptance remain separate.

The supplied executor runs unchanged ARM tests with QEMU user-mode and PRoot in
an ARM64 Trixie filesystem. This provides emulated userspace execution, not
native ARM hardware or kernel coverage. The helper probes the real guest CPU and
userspace before building, records the executor hash, and binds the work and
artifact paths plus container-local `/tmp`. An output base outside the work
directory is bound explicitly too. Native Bazel and build tools stay on AMD64.

Some existing test launchers embed exec-configured Python. For tests only, the
helper resolves the matching locked ARM standalone runtime, verifies real
ELF62/183 architectures and exact Python version/ABI, and passes complete-runtime
`--bind-at` mappings to the executor. Native interpreter files stay unchanged.
For simple shared-lock pip hubs, generated-consumer adapters select native wheels
for generators and ARM wheels for target tests, using the already selected
`rules_python` and original requirements bytes. Existing platform/index hubs and
development-only hubs remain unchanged; unsupported simple hub arguments or
changed module versions fail validation. Runtime mappings, hashes, original hub
configuration and lockfiles are retained in the cross receipts.

Cross builds may supply a readonly content-addressed Autoconf `CONFIG_SITE` that
recognizes an ARM compiler selected by a native build action. It preserves
explicit configure aliases, native compiler actions and caller-provided
`CONFIG_SITE`; it invents no cached target-probe answers. The effective site and
hash are retained. Source-owned runtime preparation executes through the guest
wrapper, preserving its locked inputs and checking an ARM receipt. Cross test
timeout defaults are 180/900/2700/7200 seconds for Bazel's four timeout classes;
explicit caller values and native defaults remain unchanged. All original build
and test labels, source checks and uncached-test requirements still apply.

The dedicated CI cross-fixture job runs all tests in `test_arm_cross_runtime.py`
with pinned native Bazel and the installed executor. Missing prerequisites or a
skipped cross test fail that job. Native unit jobs exclude this file explicitly,
so it is not counted twice or hidden among optional skips. For the same explicit
suite in a suitable disposable runner:

```sh
REGISTRY_CI_TEST_BAZEL=/usr/local/bin/bazel \
REGISTRY_CI_TEST_ARM_EXECUTOR=/usr/local/bin/sonic-arm64 \
  /usr/bin/python3 -I -S ci/run_runner_tests.py --suite cross
```

This foundation is not acceptance of the full ARM matrix. Before moving a module
row, validate its complete original build and uncached-test contract with the
native-generator/ARM-output foundation, unchanged source pins and resolution
receipts. SAI now selects the isolated provider, but
its full cross build and tests have not passed. Other known gaps include nested
Bazel/sandbox execution in rules_go, SWSS self-reexecution under emulation, and full libyang/protobuf
debugger/upstream coverage. P4C/PI source candidates and FIPS target-binutils work
remain separate module changes; transitive consumers retain their published
dependency pins. No source recipe or image change is included here.

## Local reproduction

Use a native AMD64 or ARM64 Debian trixie environment with Bazel 8.5.1 and
`binutils`, `build-essential`, `ca-certificates`, `gdb`, `git`, `python3`, `tar`,
`curl`, and `xz-utils`. From the registry checkout, inspect the plan and run the
selected module:

```sh
git fetch origin main
python3 ci/registry_ci.py plan --latest \
  --published "$(git rev-parse origin/main)" --head "$(git rev-parse HEAD)" \
  --output /tmp/registry-ci-plan.json
python3 -m unittest discover -s ci/tests -v
python3 ci/registry_ci.py run \
  --module libyang \
  --version 3.12.2.sonic.1 \
  --architecture amd64 \
  --work-dir /tmp/registry-ci-libyang-amd64 \
  --artifacts /tmp/registry-ci-libyang-amd64-artifacts
```

Use `--architecture arm64` on a native ARM64 server. `--bazel /path/to/bazel`
selects a specific Bazel executable. To inspect a PR's selection, replace
`--latest` with `--base <actual-PR-base-commit>` and check out the desired head first.
Use `--all` to include every configured historical version. Keep `--published`
set to the freshly fetched maintained `main` SHA, even for a stacked PR. Keep
the work and artifact directories outside the registry checkout and use a fresh work directory for a
clean reproduction.

See the [Bazel registry format](https://bazel.build/external/registry) for module
source, patch, and overlay metadata.

### SONiC Go pseudo-version ordering

Registered SONiC patches may retain a Go pseudo-version suffix, for example
0.0.0.sonic.1-20200309174518-a00bece872fc. The planner accepts the exact
14-digit timestamp and 12-lowercase-hex form while preserving numeric release,
SONiC patch number and separator precedence. Equal release/patch snapshots
continue to use metadata registration order; hashes/timestamps are not sorted.
Malformed or unrelated suffixes remain rejected.

## Exact ARM64 security inputs for PR151 owner-source analysis

[PR151 archive validation at `0a789dead`](https://github.com/securely1g/sonic-buildimage/actions/runs/42174896441/job/127750984306)
built the runtime and Orchagent artifacts before its unconfigured 32-root
owner/Scapy source-closure query failed on `libkadm5srv-mit12` ARM64. Its sole
selected security Snapshot URL returned HTTP 503. The same query reported
HTTP 503 for the sole selected `libsodium23` ARM64 URL; that is an observed
required-input warning, not the first fatal or proof of a separate query failure.
The already-covered libsodium ARMHF route is unchanged.

The current source-owned libteam `apt.install` declaration equals the accepted
recipe: libsodium ARM64 is directly requested, and the selected libzmq3-dev
expanded closure contains the exact libkadm5srv ARM64 package. The selected
infrastructure MODULE and source hashes also match the accepted lock. These
static bindings do not claim a retrieved failed-run lock, a direct Debian
dependency edge for libkadm5srv, or full current graph equivalence.

| Exact input | Role | Bytes | Original locked SHA256 |
| --- | --- | ---: | --- |
| [libkadm5srv-mit12_1.21.3-5+deb13u1_arm64.deb](https://snapshot.debian.org/file/5545c41ec7e7c983b9b966ba46680f4b6954f5ad/libkadm5srv-mit12_1.21.3-5%2Bdeb13u1_arm64.deb) | First fatal fetch | 53,308 | `9e25c202e883de84c2c37d8cc10cadc8fd5538cd4227a1b9f4f160ece94756d6` |
| [libsodium23_1.0.18-1+deb13u1_arm64.deb](https://snapshot.debian.org/file/283449abed3611000399635e3d5dc333b29c4c08/libsodium23_1.0.18-1%2Bdeb13u1_arm64.deb) | Required-input warning | 120,444 | `d94fc46204b65a965e356ebc19f9f88aeb20a9c777cb9a6569e75f75d0ae5523` |

One bounded filename-bearing official Snapshot request per input returned
HTTP 200 and matched the complete retained cache bytes and original SHA256.
There were no redirects, retries, metadata requests, package execution, or
manual ARM execution. Content SHA1 values locate the bytes; the original
package SHA256 remains authoritative. Only these exact dated security URLs
gain content-first routes, each followed by its exact original URL. Existing
scope tests cover changed dates, filenames, architectures, paths, hosts and
query suffixes; all previous routes and negative controls remain intact.
Configured-fetch and consumer acceptance for these additions remain pending.

### PR151 ARMHF libc-dev-bin source-query input

PR151 AMD64 archive job 127811197110 (OCI attempt 2 at `0a789dead`) passed
Orchagent validation with 106 ELF/debug pairs and 370 Scapy files, then its
32-root owner/Scapy source query stopped on
`libc-dev-bin_2.41-12+deb13u3_armhf.deb`: the official pool returned 404 and
the unchanged dated Snapshot URL returned 504. The selected infrastructure
sysroot recipe and accepted lock bind this exact ARMHF input; this is an
import during AMD64 analysis, with no manual ARM execution.

The exact dated URL now tries its verified filename-bearing Snapshot content
URL before the unchanged official-pool and original Snapshot fallbacks. One
content request returned 200 and matched all 58,444 locked/cache bytes and
SHA256 `f9797e3c0b091a540c1d33b630ba965aab9b128cb73c3c28ed4271c9e83b9354`.
The SHA1 locates the file; the original package SHA256 remains authoritative.
No metadata request, redirect, retry, package extraction or execution was used.
The historical accepted lock is provenance, not a failed-run generated lock
or a full current graph. Existing routing tests exercise this exact tuple
and retain date, package, architecture, host and path negative controls.
