# DHCP relay source registration — Draft, limited consumer validation

Direct source prerequisite: https://github.com/securely1g/sonic-dhcp-relay/pull/3, immutable 3c5fb7b55b2f2a93bbe493f8ed3eb670e8663622. Source includes attributed private-Redis fixture content from relay#1, not a second fixture-only ownership claim.

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

Maintained source PR#3 merged on 2026-11-13 at 22:30:55 UTC. Landed commit 3c5fb7b55b2f2a93bbe493f8ed3eb670e8663622 has tree c968778d6caa41e91deac52d9d344b136be7ed9b, identical to reviewed/tested head 5b95c0398622299b0b81283016b359ba13ffc5a1. Archive SHA256 ca22301b7c71aea806354ca2cbcb5ee140d82f4da19ccad11c035be10079fb12; all 103 tracked blobs and Git executable/symlink modes match. The gmock_global gitlink (6552faa2a94250ed0192dbd62e608d37fafcc216) is only an empty directory in the archive; MODULE separately declares its pinned source. No archive setup code was executed. The registry MODULE changes only the source version; its generated overlay is maintained through `sync-module`. Source review and scoped validation passed: two earlier uncached Bazel full-suite runs (47 DHCP6 / 62 DHCP4), original Make-built binaries (47/47 and 62/62, no skips) in a NET_RAW-only isolated runtime, matched runtime/debug artifacts and measured loader closure. The authoritative source APT lock contains 1122 packages; it is not replaced by a downstream consumer resolution. These are source receipts, not registry CI results. Literal DHCP4 `make all` dependency bootstrap/global installation remains NOT VERIFIED; native full LSan, default-host libyang, ARM, image/live forwarding and arbitrary future dlopen are not claimed. Successful configured source validation uses the documented trixie host platform. Hosted source run43492008222 passed six outputs and four uncached targets (sender3, classifier2, DHCP4 62, DHCP6 47) at the identical reviewed tree; this is source coverage, not registry CI. The earlier external consumer at source3f7f79c passed DHCP6 runtime/debug/metadata plus sender3. The landed delta from that source is seven CI/test-adapter/documentation files, including tests/runtime/BUILD.bazel; production sources, MODULE, locks and the declared DHCP6 consumer target package are unchanged. Those historical scoped receipts are retained, but no fresh landed-archive external-consumer build or hosted registration PASS is claimed.

Source#3 is merged → this registration remains unpublished → image remains held. No monitor source dependency. Reuse published Common .9 (including Common45 overlay), infra .26 and distroless .16. Canonical default remains securely1g main; explicit reviewed candidate checkout only for premerge validation.

```sh
python3 ci/registry_ci.py run --module sonic-dhcp-relay --version 0.1.0-3c5fb7b55b2f2a93bbe493f8ed3eb670e8663622 --architecture amd64 --work-dir /tmp/relay-registry-consumer --artifacts /tmp/relay-registry-evidence --bazel bazel
```

Use new empty directories; audit scoped configured actions before execution. No DEB-producing rule or fixture is selected. Keep Draft pending fresh graph/actions, complete parser-boundary coverage and native runtime/image acceptance.

## Local preparation hold

This landed-source repin is integrated with maintained registry helpers and a fail-closed PR planning safeguard. Necessary readiness/safeguard implementation is authorized; publication still requires exact sonic-reviewer acceptance and verified bounded predispatch checks. The original HOLD252 evidence is retained, not treated as permission to dispatch a broad matrix. No dependency upgrade, architecture expansion or new DHCP4 consumer coverage is included. Fresh bounded native consumer results and actual hosted CI must be recorded separately before claiming registration readiness.
