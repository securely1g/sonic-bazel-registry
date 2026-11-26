# DHCP relay source registration

Register native AMD64/Trixie DHCPv4 and DHCPv6 source builds from
[`securely1g/sonic-dhcp-relay@1bbc612265bfc8e7582cb699dc44326f62595739`](https://github.com/securely1g/sonic-dhcp-relay/commit/1bbc612265bfc8e7582cb699dc44326f62595739).
The registry version adds the immutable source commit to the owner's unchanged
`0.1.0` base version. The generated MODULE overlay changes only that identity;
compilation, runtime fixtures and packaging interfaces remain source-owned.

The source consumes the published native `pcapplusplus@24.9.0.sonic.1` target,
including SONiC's existing DHCP source-port patch. It no longer carries a private
PcapPlusPlus build or root parser-generator patches. The consumer selects the
same published `sonic-build-infra@0.0.39-81476192bf2cdb70bb646e85935c5d698b6de8a0`
APT lock as the source; it introduces no component-private lock or source override.

## External-consumer validation

The AMD64 manifest builds six public outputs:

| Producer | Runtime | Symbols | Package metadata |
| --- | --- | --- | --- |
| DHCPv4 | `//dhcp4relay:runtime` | `//dhcp4relay:runtime.debug_symbols` | `//:dhcp4_metadata` |
| DHCPv6 | `//dhcp6relay:runtime` | `//dhcp6relay:runtime.debug_symbols` | `//:dhcp6_metadata` |

It executes all four source-owned acceptance targets uncached:
`//tests/runtime:sender_test` (3 cases), `:pcap_patch_test` (2),
`:v4_full_suite_test` (62), and `:v6_full_suite_test` (47). These preserve the
original assertions and private Redis fixture, using declared ELF runtimes and
Python instead of requiring Docker inside the registry worker. The source CI
also verifies the 114 individual test cases have no failures, disables or skips.
Registry evidence retains their XML reports for the same review.

The independent `//:archive_contract_test` checks both installed executable paths,
AMD64 ELF identity, runtime/debug build IDs and debuglink CRCs, root ownership,
fixed TAR timestamps and package metadata bound to the runtime TAR digest.
The shared ELF parser is reused; no target binary executes on the host loader.

The checked-in consumer MODULE makes the source root's supported Bazel 8.5.1
GCC, Python and Rust selections explicit. All validation outputs are TARs,
metadata or test results. No DEB-producing target or fixture is selected.

```sh
python3 ci/registry_ci.py run \
  --module sonic-dhcp-relay \
  --version 0.1.1-bb94f3d743c908cab3ff99f9cfb694d5a0d4e06e \
  --architecture amd64 \
  --work-dir /tmp/relay-registry-consumer \
  --artifacts /tmp/relay-registry-evidence \
  --bazel bazel
```

Use empty job-local work/evidence directories. Audit the configured consumer
action graph for DEB-producing outputs before dispatching this manifest. The
maintained registry runner then checks the fetched identity, declared outputs
and uncached test results. A prepared manifest is not a native test result;
retain the exact-head CI receipts before claiming the registration passes.

## Landing order

The source prerequisites [DHCP relay PR #4](https://github.com/securely1g/sonic-dhcp-relay/pull/4)
and [PR #5](https://github.com/securely1g/sonic-dhcp-relay/pull/5) are merged. This entry
selects PR #5's actual landed commit on `master`, not its former PR-head snapshot.

Validate this exact registry candidate before landing the registration. The
separate DHCP relay image integration consumes the resulting module. Canonical registry defaults
remain `securely1g/sonic-bazel-registry/main`; a candidate revision is used only
for explicitly selected premerge validation. DHCP monitor and ISC DHCP are
separate existing source owners, not reimplemented by this module.

Archive SHA256: `ebf5d7fab4749b5a4837cd8d72b1f0c2fef0a28c3255a745e3ecd62f5da53cce`. All 90 tracked source blobs, Git file types and executable bits match the owner commit. The `gmock_global` gitlink is fetched by its separately pinned source declaration.
