# Sairedis library package metadata

This candidate registers [source PR #9](https://github.com/securely1g/sonic-sairedis/pull/9), including the unchanged library-metadata feature from [source PR #8](https://github.com/securely1g/sonic-sairedis/pull/8). It continues the same work as [registry PR #157](https://github.com/securely1g/sonic-bazel-registry/pull/157) in a securely1g-owned branch; those original proposals remain open and are not separate build prerequisites.

`@sonic_sairedis//:library_runtime_packages.json` describes only `libsairedis` and `libsaimetadata`, using their original package controls and exact source runtime TAR hashes. The existing aggregate metadata and source-built library, Syncd and VS SAI TARs remain available.

The concrete `sonic-buildimage` P4RT debug consumer needs `libsairedis.so.0.0.0`, `libsaimeta.so.0.0.0` and `libsaimetadata.so.0.0.0`, together with their matching symbols. Selecting this library metadata avoids building unrelated Syncd and VS SAI outputs merely to generate package records. SWSS/Orchagent and Syncd/Gearbox also consume these libraries; their image validation remains separate.

The source and ordinary consumer select the published `sonic-build-infra@0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88` metadata tools. The previous unpublished `1341eaf` input is unavailable on maintained main. All other producer inputs and the original 19 build targets/seven tests are retained. Both existing AMD64 and ARM64 consumer lanes remain; the new P4RT image work is AMD64 only. No DEB producer is selected.

Source configured-graph and CodeQL preparation checks passed locally. Source package tests, actual CodeQL extraction and this ordinary registry consumer are tracked by their current-head CI; graph analysis is not a complete package or image acceptance claim.
