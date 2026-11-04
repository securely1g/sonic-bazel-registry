# Sairedis library package metadata

This candidate registers [source PR #9](https://github.com/securely1g/sonic-sairedis/pull/9), including the unchanged library-metadata feature from [source PR #8](https://github.com/securely1g/sonic-sairedis/pull/8). It continues the same work as [registry PR #157](https://github.com/securely1g/sonic-bazel-registry/pull/157) in a securely1g-owned branch; those original proposals remain open and are not separate build prerequisites.

`@sonic-sairedis//:library_runtime_packages.json` describes only `libsairedis` and `libsaimetadata`, using their original package controls and exact source runtime TAR hashes. The existing aggregate metadata and source-built library, Syncd and VS SAI TARs remain available.

The concrete `sonic-buildimage` P4RT debug consumer needs `libsairedis.so.0.0.0`, `libsaimeta.so.0.0.0` and `libsaimetadata.so.0.0.0`, together with their matching symbols. Selecting this library metadata avoids building unrelated Syncd and VS SAI outputs merely to generate package records. SWSS/Orchagent and Syncd/Gearbox also consume these libraries; their image validation remains separate.

The source and ordinary consumer select Common `.8-4359814`, infrastructure
`.26-2cfc059`, libnl `3.7.0.sonic.7` and published Distroless `.16`.
The explicit review base contains the exact selected prerequisite entries,
including libnl's SDK timestamp normalization. It preserves every published
entry. Only the sole unpublished Sairedis `.4` candidate is replaced here;
there is no source repository override or second packaging definition.

The original 19 build targets, seven component tests and both native AMD64/ARM64
consumer lanes remain. The source's ELF test children use Common's declared
loader/runtime/patchelf interface. The new P4RT image work is AMD64 only, and no
DEB producer is selected. Direct prerequisites are source #9 and registry
#201/#181/#209; the original proposals #8/#157 remain historical references.

The source graph covers all 358 original sources and 366 ownership pairs.
Local library metadata/runtime acceptance retained the exact two package
records and three library ELFs. All seven original Bazel targets pass across
the retained run and focused declared-runtime retry: 419 passed XML cases and
two original PaValidation applicability skips. The runtime retry adds only
the two owner library TARs to the affected test fixture; original C++ code is
unchanged. That evidence stays bound to its recorded inputs and preceding
review catalog.
Current-head source/CodeQL and ordinary registry acceptance are separate CI
gates; this Draft registration does not claim downstream image acceptance.

Source `ee19458a` (landed master from PR #9) additionally fixes the standalone `bazel --version` query in
the review CI launcher. Its archive differs from `7c49be4d` only in that CI
helper and its regression test; native build, runtime and original test inputs
are byte-identical. The prior `fea55db`/`7c49be4d` ARM64 ordinary consumer has
44 independently verified outputs and seven XMLs (419 passes/two original
applicability skips). Those receipts remain bound to the prior candidate.
Actual new-head payload equality, source package-contract and registry native
acceptance remain pending; source-input equality alone is not artifact proof.
