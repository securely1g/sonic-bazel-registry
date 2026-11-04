# Module ZIP download caching

Based on upstream Gazelle v0.54.0. The patch adapts the explicit ZIP lock design
from sonic_rules gazelle@0.47.0.sonic.2. It adds a root `go_deps.zip_lock` tag,
exports structured update plans with resolved versions, Go content sums and the
host-compatible rules_go SDK, and adds the same plan interface to explicit
`go_repository` declarations configured with `zip_sums`.

Normal module ZIP downloads use `repository_ctx.download(sha256=...)` and retain
Go h1 validation. The fetcher checks the ZIP and checksum before extraction,
uses golang.org/x/mod/zip, then copies validated files into the repository.
The upstream x/mod v0.23.0 zip package is included alongside Gazelle's existing
vendored x/mod packages so repository tool bootstrapping stays offline.
Its copyright and BSD license remain in vendor/golang.org/x/mod/LICENSE.

Ordinary downloads use the first HTTP(S) GOPROXY source. An unset or empty
GOPROXY uses Go's default `https://proxy.golang.org,direct`; its proxy ZIP URL
works with both local and remote Bazel downloaders. Later proxy entries and
direct repository fallback remain unimplemented: a failed first download reports
the original error and the unattempted fallback. Initial `direct` and `off`
produce diagnostics only when a module repository is fetched; `off` prohibits
downloads. Neither value prevents dependency-lock plan export. Proxy bypasses
require an explicit alternative; the patch never silently substitutes a public
proxy. Explicit updates use the shared sonic-build-infra Go updater and the
configured Go SDK. Unconfigured upstream extensions retain upstream behavior;
root-configured ZIP locks are strict and fail on missing digests.

The new source tests cover content checksums, invalid module paths and a ZIP
stored inside the target repository. Registry CI runs them through an external
consumer. Cache-restoration evidence and root integration checks are recorded
separately for the candidate.

The GOPROXY URL regression follows https://go.dev/ref/mod#goproxy-protocol.
The patch is maintained here and has not been submitted upstream.
