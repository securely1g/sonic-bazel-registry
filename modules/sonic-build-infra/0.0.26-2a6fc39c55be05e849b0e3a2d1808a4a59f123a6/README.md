# Unique APT layer paths with the retained native build rules

This replaces [registry #209](https://github.com/securely1g/sonic-bazel-registry/pull/209)'s sole unpublished `.26` candidate with its exact source plus [infra #81](https://github.com/securely1g/sonic-build-infra/pull/81). Combined source `2a6fc39c55be05e849b0e3a2d1808a4a59f123a6` is a direct child of accepted `2cfc059c2cf1dc3b2f2b2ec1bcd70400b04ecb75`; all prior native tools, compiler-option transport, metadata rules and registry patches remain. Published entries are unchanged.

[Gearbox image #154](https://github.com/securely1g/sonic-buildimage/pull/154)'s actual 254 selected package TARs produce a 1.6 GB APT layer containing 2,140 repeated directory headers across 139 paths. Strict OCI validation rejects it. The owner now enables the standard Distroless `flatten` deduplication option, which keeps the last normalized path occurrence and preserves normal TAR overlay behavior.

| Input or action | Before | After |
| --- | --- | --- |
| Actual Gearbox runtime APT layer | Duplicate directory headers fail OCI validation | Unique paths; all 32,372 installed records retain bytes, types, modes, owners and link semantics |
| Two packages share directory headers | 14 headers for 9 unique paths fail the regression | One header per path, with both packages' payloads retained |
| A later non-ELF configuration file overrides an earlier file | Last payload and metadata win | The same valid overlay remains |

The real action replay with declared tools reproduces the original layer SHA256 `655c7a8bdef9adbd84026cf0410535976e0e16848dabf6cd535d5359efc5bee8`; deduplication produces `1b00ef180abc08c02c088d4d11e83bb68bba60fd064895728a5fc2220198ba31`. Standard flatten may add a harmless `./` link prefix; comparison removes only dot components, preserving absolute and traversal distinctions.

Native AMD64/Trixie source tests pass the four original adapter cases and two new overlap/override cases. Removing only the new option reproduces the uniqueness failure while the valid non-ELF override still passes. The configured source test audit has 263 actions/352 outputs with no DEBs or package-building wrappers.

Presubmit retains all 42 prior outputs and 43 tests, and adds the actual overlap layer/selection receipt plus the original adapter and new overlap tests. The ordinary consumer explicitly selects published Distroless `.16`, matching Gearbox's actual graph; the owner's minimum remains unchanged. Full current-entry ordinary/hosted acceptance and the integrated Gearbox image validation are pending. The fixtures create TARs only, and no DEB producer is introduced.

This feature remains Draft on unlanded source #81 and registry #209's cumulative prerequisites. Do not replace an active consumer pin before its validation boundary. The cumulative comparison from published `.25` includes every retained `.26` source patch, overlay and test input.
