## Registry dependency refresh: `2.0.2-901ad836260466c17c08a4ab0e0d311e4a2d124e`

Source: `securely1g/sonic-py-swsssdk@901ad836260466c17c08a4ab0e0d311e4a2d124e`, based on `829c26c9d55d02e0017d763dae4f439d61ad8658`. Dependency targets are frozen to published registry snapshot `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. The source owns the module base version and dependency updates. The registry supplies the full commit-qualified identity and retains its existing integration behavior.

Full archive patch-application and build validation must be recorded separately.

# sonic-py-swsssdk Bazel registration

This entry fixes the sonic-buildimage submodule revision
`5878f93779df1bfdfe58ea00c8d34fe8261d362e` and the upstream Python distribution
`swsssdk` version `2.0.1`. The original source archive is downloaded from
sonic-net; registry overlays supply the Bazel build declarations and test
entry point. Production Python sources remain in that archive.

Public interfaces:

- `:swsssdk`: Python library and configuration resource.
- `:swsssdk.wheel`: pure Python `swsssdk-2.0.1-py3-none-any.whl`.
- `:swsssdk.runtime`: direct source installation TAR under
  `/usr/local/lib/python3.13/dist-packages`, with PythonRuntimeInfo linking the
  separate `redis-dump-load` installation.
- `:swsssdk.runtime_metadata`: transitive source package metadata.
- `:upstream_tests`: the unchanged upstream pytest suite with managed Python.

Wheel and direct installation share the effective setup.py metadata. The
ordinary-import deprecation error and empty command entry points are preserved.
Image/rootfs consumers resolve third-party runtime dependencies from the
Requires-Dist declarations; the test dependency lock fixes the library's Redis
and test environment inputs.

The independent registry consumer checks payload bytes and distribution fields
against the original setup.py, wheel and installed RECORD hashes, installation
attributes, package resources, the deprecated import, and transitive runtime
metadata. Source-owned build and upstream-suite results are reused when their
inputs are unchanged; registry consumption separately verifies archive and
overlay acquisition.

The overlay MODULE is generated from this entry's MODULE using
`ci/registry_ci.py sync-module`. Refresh source.json integrity values whenever
maintained overlay inputs change. The requirements input and hash lock travel
together with pip.parse.
