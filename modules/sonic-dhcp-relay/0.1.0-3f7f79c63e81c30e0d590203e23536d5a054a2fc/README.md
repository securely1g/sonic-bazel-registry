# DHCP relay source registration — Draft, limited consumer validation

Direct source prerequisite: https://github.com/securely1g/sonic-dhcp-relay/pull/3, immutable 3f7f79c63e81c30e0d590203e23536d5a054a2fc. Source includes attributed private-Redis fixture content from relay#1, not a second fixture-only ownership claim.

## Explicit coverage and root patch obligations

The initial registry runner manifest covers native AMD64 DHCP6 runtime/debug TARs, its installed package metadata, and the real sender unit test (three cases). **It does not cover DHCP4/PcapPlusPlus or the original full DHCP4/6 suites.** The source-owned full-suite Docker runners require a local Docker daemon and are not executable in the registry's container without additional infrastructure.

DHCP4 requires the source-owned m4/bison/flex parser-generator patches. `single_version_override` is root-only: those overrides in the dependency MODULE do not propagate. The registry runner disallows source overrides in checked-in integration modules, and its generated consumer has no patch-override schema. Rather than silently dropping patches or knowingly configuring broken coverage, the initial manifest explicitly limits itself to the independent DHCP6 slice. Complete DHCP4 registry validation remains a Draft acceptance gate, not a claimed pass. The coordinated image root carries byte-equivalent parser patches explicitly. Standalone consumers must make the following root selections (or use separately reviewed equivalent registry versions):

```starlark
single_version_override(module_name = "m4", version = "1.4.21.bcr.8", patches = ["@sonic-dhcp-relay//third_party/patches:m4-wrapper-headers.patch"], patch_strip = 1)
single_version_override(module_name = "bison", version = "3.8.2.bcr.13", patches = ["@sonic-dhcp-relay//third_party/patches:bison-wrapper-headers.patch"], patch_strip = 1)
single_version_override(module_name = "flex", version = "2.6.4.bcr.10", patches = ["@sonic-dhcp-relay//third_party/patches:flex-wrapper-headers.patch"], patch_strip = 1)
```

Preserve the source README's tar/rules_cc and root Rust toolchain selections as well. This entry does not invent patched upstream versions, rewrite old registry entries or modify shared registry CI.

## Evidence and order

Archive integrity and all 98 tracked source blobs match the published reviewed source. The registry MODULE changes only the source version; its generated overlay is maintained through `sync-module`. Source review and scoped validation passed: two earlier uncached Bazel full-suite runs (47 DHCP6 / 62 DHCP4), original Make-built binaries (47/47 and 62/62, no skips) in a NET_RAW-only isolated runtime, matched runtime/debug artifacts and measured loader closure. The authoritative source APT lock contains 1122 packages; it is not replaced by a downstream consumer resolution. These are source receipts, not registry CI results. Literal DHCP4 `make all` dependency bootstrap/global installation remains NOT VERIFIED; native full LSan, default-host libyang, ARM, image/live forwarding and arbitrary future dlopen are not claimed. Successful configured source validation uses the documented trixie host platform. Fresh external-consumer validation of this exact registration must be recorded separately.

Merge source#3 → this registration → image. No monitor source dependency. Reuse published Common .9 (including Common45 overlay), infra .26 and distroless .16. Canonical default remains securely1g main; explicit reviewed candidate checkout only for premerge validation.

```sh
python3 ci/registry_ci.py run --module sonic-dhcp-relay --version 0.1.0-3f7f79c63e81c30e0d590203e23536d5a054a2fc --architecture amd64 --work-dir /tmp/relay-registry-consumer --artifacts /tmp/relay-registry-evidence --bazel bazel
```

Use new empty directories; audit scoped configured actions before execution. No DEB-producing rule or fixture is selected. Keep Draft pending fresh graph/actions, complete parser-boundary coverage and native runtime/image acceptance.
