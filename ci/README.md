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
passes only when planning and the runner's unit tests pass, and every selected
module job passes. A skipped module matrix is accepted only after successful
planning explicitly selected no jobs. Adding the workflow does not itself change
repository branch-protection settings.

## Verified source mirrors

The runner passes Bazel's standard `--experimental_downloader_config` with
[`source_mirrors.cfg`](source_mirrors.cfg) to dependency preparation, builds,
tests and output queries. Rewrites match only the archive and binary-package
URLs and one exact dated package index described below; registry order, module versions, source recipes and
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

[PR196 native FRR analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42127542383/job/127595462127) could not obtain any format of the dated `trixie-updates/main/binary-arm64/Packages` index: xz/gz/bz2 returned HTTP 503 and plain Packages returned HTTP 404. One later original-xz request returned HTTP 504. The exact xz URL now tries the [official content address](https://snapshot.debian.org/file/c9d85a145fcc34817defe65c818ded141ea2c95f), then its unchanged original URL. One complete HTTP 200 content download matched the retained 4,424-byte cache and same-URL index fact (SHA256 `fe771d58d4af39dbb94142d6f3ce578d340c6b1364c172d9e87f2287bdc4994b`) in an accepted earlier native artifact. This is not a failed-run lock or signed Release verification: the selected Distroless resolver does not verify Release/InRelease, and supplies fact integrity only when available. No other suite, architecture, date or index format is rewritten; all generic index exclusions remain. Configured-fetch and current consumer acceptance are pending. No package was generated or executed.

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

## Exact Socat source archive fallback

The [SWSS image source-base workflow at `6ab506bd`](https://github.com/securely1g/sonic-buildimage/actions/runs/42055651322/attempts/2)
failed fetching `socat_1.8.0.2-1.debian.tar.xz` from both declared Snapshot hosts.
Its [selected Socat recipe](https://github.com/securely1g/sonic-bazel-registry/blob/ccd4d6c2a6e3551f40e0d973ef5756006eba7e9d/modules/socat/1.8.0.2.sonic.3/MODULE.bazel)
pins SHA256 `04b361cd91884eda6ca9fe2890ca83a6abe73dd8ce75fe9927b2d8443af36123`.
One official content GET returned the identical 15,148 bytes from
`https://snapshot.debian.org/file/0475522901bd85478b944520b23e01e3f3c7d339`.
The SHA1 path locates the file; the existing repository rule still verifies the
unchanged SHA256 before extracting Debian's patches.

Only that exact timestamped `snapshot.debian.org` source URL now tries the
verified content address before its original URL. Other source archives,
including Socat's distinct `orig.tar.bz2`, indexes, near-miss versions and dates,
and the separately declared Cloudflare URL remain unchanged. Pure routing tests
check the exception and those exclusions. The GET proves byte availability;
new configured fetch and image acceptance remain pending.

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

- `architectures`: native execution and target architectures to validate,
  currently `amd64` and/or `arm64`.
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

ARM64 jobs continue to use native GitHub-hosted `ubuntu-24.04-arm` runners.
Moving them to AMD64 containers with cross compilation is a separate change.
ARM64 module jobs retain the
`debian:trixie-20260918` container pinned to its multiarch image digest. AMD64
steps execute directly inside the disposable runner, built from that same
pinned Trixie base with the compiler and package-test tools preinstalled.
AMD64 does not start a second container or require a Docker daemon. Actions run
as UID 1000; module validation and runtime package preparation use passwordless
`sudo` inside the disposable container. Evidence is archived as root, then only
the resulting TAR is given to the action user, preserving the archived modes.

The manager supplies `SONIC_RUNNER_IMAGE_REFERENCE=sonic-slave-runner@sha256:...`
from the actual derived image's inspected Docker image ID. This is a local
content identity, not a registry pull reference or the upstream base digest.
`validation.json` records that AMD64 identity or the ARM64 pinned job image
reference. Missing AMD64 identity fails validation. Runtime preparation receipts
also record the prepared package inventory and library hashes.

The AMD64 image contains the checksum-verified Bazel 8.5.1 binary at
`/usr/local/lib/bazel-8.5.1`. Its `/usr/local/bin/bazel` wrapper explicitly passes
the image's Java CA trust store as a startup argument, including when CI ignores
all bazelrc files. The workflow verifies the binary's checksum again. ARM64
downloads and verifies its native Bazel binary in the job container. GitHub
actions are pinned to commit SHAs, checkout does not
persist credentials, and the workflow uses read-only repository permissions.

AMD64 module jobs pass `--bazel-startup-arg=--host_jvm_args=-Xmx2g` to bound
Bazel's Java heap within each runner's 16 GiB memory limit. The runner accepts
repeated startup arguments, forwards them to build, test, cquery, info and Rust
preparation, and records them in `validation.json`. ARM64 keeps its default heap.
Repeated `--bazel-build-arg` options reach build, test and output queries.
AMD64 jobs use `--jobs=1` and `--discard_analysis_cache` to reduce concurrent
compiler memory; Rust preparation receives those settings too. This limits
concurrent Bazel actions; recipes may still request parallel compilation inside
an action. The declared targets and published recipes stay unchanged. The AMD64 module matrix runs at most
ten jobs concurrently; the sixteen registered workers also serve planning, unit
tests and subsequent jobs. Native ARM64 validation has its own matrix, so queued
hosted jobs do not consume AMD64 matrix slots. Both matrices are required by the
aggregate check.

Tests receive an explicitly exported empty `HOME`, which Bazel's test setup
replaces with that test's writable `TEST_TMPDIR`. This lets Python and other
subprocesses create user configuration inside the test sandbox; an absent
`HOME` would otherwise fall back to the account's home directory.

`TestRunner` actions prefer `processwrapper-sandbox`. This lets tests hard-link
their declared runfiles into writable temporary directories and set executable
permissions on those private copies. Build actions keep their existing sandbox
strategy. Local or exclusive tests retain the `local` fallback, and real Bazel
regressions cover both paths without changing published tests.

Runner tests execute on native AMD64 and ARM64 hosts with pinned Bazel 8.5.1.
They build an actual directory-producing target and its public alias, including
both target and execution configurations, then check collection and extraction.
Transport and failure-log tests also cover rejected paths, partial archives,
case-sensitive filenames, Unix modes, empty directories and symlink relocation.

Each job uses a fresh consumer and Bazel output directory. There is no saved Bazel
cache in this initial workflow. Logs, Bazel build-event files, available test
logs, and validation metadata are retained as workflow artifacts for 14 days,
including when module validation fails. Setup failures can occur before these
files exist and remain visible in the Actions job log.

ARMHF, cross execution, other operating systems, all historical registry entries,
and the complete SONiC image are outside this matrix. Declaring an ARMHF layout
in a module does not establish ARMHF build or execution coverage.

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
