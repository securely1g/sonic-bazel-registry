# Debian installation links for Syncd

This candidate registers [build-infra #68](https://github.com/securely1g/sonic-build-infra/pull/68) for [buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13). The source TAR targets provide compiler, Automake and OpenMPI aliases without an image-side installation-state snapshot.

The previous published .23 entry remains unchanged. Both numbered patches, validation overlays and all inherited build/test selections are retained; the version patch identifies this source commit. Native AMD64 and ARM64 presubmits additionally build the three alternatives TARs and test their headers and link chains.

The source PR is unmerged, so this registration remains Draft.
