# SONiC's shared ygot dependency

Management-common's generator and runtime libraries use ygot 0.7.1 with the
existing SONiC schema/validation changes. This entry retains that source and
its SONiC patches while moving dependency ownership out of the consumer. `//generator:generator`, `//ygen`, `//ygot` and `//ytypes` are public
targets. They depend on the shared `openconfig_goyang` target, so callers and
generated bindings use the same Go `yang.Entry` type.

The source is upstream `v0.7.1`. Its existing SONiC Make/vendor patch and union
enumeration-order fix are copied unchanged from management-common's accepted
`f5361ba8b88cde7ec59bdb4652a986c68d66da64` source. The old Bazel patch that added
`@com_github_openconfig_gnmi//value` is represented directly in the maintained
`ytypes/BUILD.bazel` dependency list. It no longer patches another repository's
generated BUILD file during the consuming build.

The component BUILD definitions reuse the accepted management-common dependency
graph. They retain the original source/test lists and production protobuf rules;
they are checked-in definitions that can be edited beside the corresponding
components. Standard `proto_library` import prefixes match the upstream protobuf
imports. Demo protobuf fixtures use the Go files shipped by v0.7.1, preserving
their original package names instead of regenerating a different API. Declared
generator actions reproduce the original `go:generate` preparation for the four
demo/integration schema packages before their tests. Gazelle remains an optional
maintenance command. Normal builds do not regenerate these BUILD files. Unused generated package-metadata helpers are
not copied.

The Go lock overlay declares the dependency versions already selected by the
accepted SONiC build, including protobuf 1.36.11, gRPC 1.82.1, split genproto RPC
and the selected 2020 gNMI/goyang revisions. It does not upgrade ygot's source.
The ordinary registry integration consumer retains management-common's existing
glog replacement and checked-in gNMI protobuf setting. It compiles and tests a
direct goyang schema passed to ygot's public validator, including an invalid
value rejection. Standard Gazelle module mapping supplies the shared Go type
identity; no custom resolver is used.

Native AMD64/Trixie acceptance with Go 1.25.9 passes all 26 targets and 1,545
reported test cases without skips: all 24 original targets, the new union-order
regression and the separate shared-type consumer. The actual generator is built
and exercised. All 329 original test functions remain, with fixture adaptations
described below. Build and test action audits contain no DEB outputs. Removing only the historical
union-order patch makes the same regression fail: declared `ZULU, ALPHA` becomes
`ALPHA, ZULU` in the generated reflection map; the complete candidate preserves
the declared order.

This entry depends on shared goyang [registry #212](https://github.com/securely1g/sonic-bazel-registry/pull/212).
Management-common's actual 20-generation, CVL/translib and output-restoration
checks remain pending. Registry #165 and active image pins stay unchanged until
that consumer acceptance passes.

The full original suite exposes compatibility gaps that the former consumer did
not execute. Additional numbered patches keep their scope explicit:

- `0003` backports upstream [PR 377](https://github.com/openconfig/ygot/pull/377)
  only for `testcmp`/`testutil` and their tests. Standard `protocmp` handles the
  already-selected protobuf API; the old exported `JSONIETFComparer` signature
  remains. No Go dependency version changes are included.
- `0004` checks actual Go assignability after the existing bool, binary and
  pointer conversions. An incompatible `[]string` assigned to a derived
  `[]byte` field now returns the original test's expected error instead of
  panicking. Valid conversions and interface assignments remain covered.
- `0005` initializes old handwritten/pre-generated test schemas with the
  performance state created by the SONiC parser. It also tests the existing
  enabled/disabled debug behavior and compares compact demo JSON against every
  original expected token. The helper is a Bazel `testonly` dependency.

The original two SONiC patches remain byte-identical. The cumulative runtime
source includes the separately documented corrections below, so the full
runtime tree is not claimed unchanged. Legacy Make/vendor inputs are unchanged
at this stage and still contain the inherited defects described here. All 26
test targets remain enabled; management-consumer validation is required before
adoption.

The full original tests also expose small inherited defects. These corrections
are kept separate from the byte-identical historical SONiC patches:

- `0006` records the existing SONiC schema metadata in the five JSON goldens.
  Every original key/value remains; the additional ordering, performance and
  module metadata comes from the unchanged accepted generator.
- `0007` passes binary values into the existing length validator. The old
  upstream branch left the value unset and accepted invalid lengths.
- `0008` uses the existing nil/default predicate for unknown container fields,
  avoiding `reflect.IsNil` on scalar values while retaining rejection of
  non-default unknown fields and the SONiC readonly handling.
- `0009` handles standalone leaf schemas with no parent. The existing parsed
  leaf-list conversion remains unchanged.
- `0010` preserves destination-only map entries during merges, as the retained
  public API and management-common subscription coalescing require. It retains
  SONiC's deep key matching and source-key choice, including equal-content
  pointer keys, without duplicating those keys or changing conflict handling.

- `0011` restores the existing annotation marshaler dispatch. RFC7952 metadata
  continues to use `Annotation.MarshalJSON`, including its existing error
  checks; normal fields retain SONiC's optimized tag-path cache.
- `0012` lets annotation fields reach their existing setter without requiring
  a YANG schema. Normal fields still reject missing schemas.

- `0013` reuses upstream PR 377's original path-copy test adaptation to standard
  `protocmp`, retaining comparison of private path state and every assertion.

SONiC's historical performance patch intentionally emits compact JSON without
calling `Validate`; `Indent`, `SkipValidation` and `ValidationOpts` do not change
that behavior in this selected version. Fixture expectations preserve those
existing defaults. Original invalid-value assertions call `Validate` explicitly,
and JSON checks compact only whitespace while retaining every expected token.
The leafref fixture prunes only empty branches created by `BuildEmptyTree`, so it
does not introduce unrelated read-only containers into the tested configuration.

- `0014` updates only the embedded gzip schema literals in the five generated-code
  goldens. Decompression matches the already-verified additive SONiC JSON
  metadata in `0006`; every byte outside those literals remains unchanged.
