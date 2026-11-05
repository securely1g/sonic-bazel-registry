# Declared-loader FIPS source registration

Direct source prerequisite: https://github.com/securely1g/sonic-fips/pull/16, immutable 429b0668a80fabc3d05b3fb67ccda900d863ae3c. The `.5` release avoids an unchanged published `.4` outranking the loader fix. Registry #221 is unrelated old-main version reconciliation and is not the fix.

Retains the existing published native AMD64/ARM64 registry runtime/debug and package/provider test matrix, without claiming either architecture has passed for this candidate. No existing entry or CI coverage is removed. Native configure adapter regressions run in the source workflows, which install Autoconf; they are not added to registry tests because the registry runtime lacks that declared host fixture prerequisite. Source runtime/crypto/upstream suites remain separate gates.

Fresh local source evidence: two real native GCC14/Autoconf configure fixture tests passed (including positive/negative runtime probes and generator-change rejection). Shell/AST/whitespace checks passed. Fresh configured source build/test analysis hit pinned snapshot HTTP504 and was cancelled within its bound; no new native artifact, full source test or configured action-audit pass is claimed. Historical November 1 integration evidence belongs to a frozen graph, not this registration. No FIPS certification claim.

Archive integrity and representative source bytes verified; generated MODULE overlay and entry validation checked. Source must land before this registry entry, and the coordinated DHCP image consumer follows. Canonical default remains securely1g main; this candidate is not available there before merge. Explicit candidate validation (fresh empty directories, after scoped action review):

```sh
python3 ci/registry_ci.py run --module sonic-fips --version 0.0.5-429b0668a80fabc3d05b3fb67ccda900d863ae3c --architecture amd64 --work-dir /tmp/fips-registry-consumer --artifacts /tmp/fips-registry-evidence --bazel bazel
```

Keep Draft pending fresh graph/actions, source/runtime and downstream image validation. Runtime/debug TARs and installed metadata are not DEB production.
