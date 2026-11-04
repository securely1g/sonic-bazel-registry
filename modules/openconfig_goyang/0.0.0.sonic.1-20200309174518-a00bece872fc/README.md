# SONiC's shared goyang dependency

Management-common's generated bindings and its ygot 0.7.1 dependency use
`yang.Entry.DirOKeys`, `yang.Entry.PerfOpts` and `yang.PerformanceOpts` from
SONiC's existing patched goyang source. This entry owns that implementation
and its schema-ordering regression tests, so consumers can select one shared
Go library without supplying reusable dependency patches from their own root.

The source remains upstream commit
`a00bece872fc729c37e32bc697c8f3e7eb019172`. Both production patches are byte-identical to
the accepted management-common implementation at
`f5361ba8b88cde7ec59bdb4652a986c68d66da64`:

- The existing Make/vendor patch retains SONiC's annotation formatter,
  ordered-entry API and cached type/validation fields.
- The existing ordering repair retains declared grouping/choice order and
  deterministic augment and identity traversal.

The user explicitly approved this shared version after reviewing BCR's
`openconfig_goyang@1.6.3.bcr.1`: that source lacks the three API fields above,
and the unchanged legacy patch fails eight hunks against it. BCR's BUILD
definitions are reused here, adjusted for the actual 2020 source files and
the legacy `annotate.go` addition. All original Go source and test files are
declared. The 2020 repository predates `go.mod`; the overlay supplies its
existing Go import identity and verified dependency locks. Test dependencies
use management-common's accepted versions, and the CLI uses BCR's pinned
`github.com/pborman/getopt@v1.1.0`.

The registry version puts `.sonic.1` in the release portion of Bazel's relaxed
semantic version. Gazelle's standard strict-version comparison therefore
retains the exact Go pseudo-version
`v0.0.0-20200309174518-a00bece872fc`. Standard `go_deps.from_file` registers
this module as the provider of `github.com/openconfig/goyang`; no custom
resolver or duplicate Go type graph is introduced.

Public targets are `//:goyang`, `//pkg/indent` and `//pkg/yang` (including the
existing `go_default_library` aliases). The ordinary registry consumer builds
the actual CLI and runs all original indent/yang tests plus focused SONiC
choice, grouping, augment and identity-order regressions with Go 1.25.9 on
native AMD64/Trixie. The new regression must also reject the unpatched
ordering behavior before adoption. Local ordinary-consumer acceptance passed the CLI and all four test targets
(86 XML cases). Removing only the ordering repair makes the same choice,
grouping/augment and identity regressions fail; the description contract still
passes. Fresh hosted CI and the later management-common/ygot consumer update
remain separate gates. No image or DEB output is claimed.

The original upstream suite remains enabled. A separate test-only patch updates
its exact JSON goldens for SONiC's existing `DirOKeys` and `PerfOpts` fields and
asserts the existing empty `Entry.Description` memory contract. No assertions or
cases are removed. A new regression additionally verifies that the original
AST description remains intact. The root YANG fixtures are explicit runfiles.
These changes do not alter either original production patch.
