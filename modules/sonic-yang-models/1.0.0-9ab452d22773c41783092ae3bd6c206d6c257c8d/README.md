# SONiC YANG models

This module provides the prepared YANG models used by schema generation and the
runtime package installed at `/usr/local/yang-models`.

## Source and version

The source is `src/sonic-yang-models` from SONiC buildimage commit
[`9ab452d22773c41783092ae3bd6c206d6c257c8d`](https://github.com/sonic-net/sonic-buildimage/tree/9ab452d22773c41783092ae3bd6c206d6c257c8d/src/sonic-yang-models).
`source.json` downloads an exact retained copy of the full upstream source
archive from this registry's
[source release](https://github.com/securely1g/sonic-bazel-registry/releases/tag/source-sonic-buildimage-9ab452d22773c41783092ae3bd6c206d6c257c8d),
extracting only this package. Its SHA-256 is
`006f73ee4e03bbfb1cf03910ebabdc2c0798f64098b1379777c9f70d5e538555`,
the same archive and integrity used by Common's standalone YANG build.
Retaining these bytes avoids depending on GitHub regenerating an identical
archive; the upstream commit remains the source provenance. No production
source file is patched. Its setup.py package version `1.0` is represented as
Bazel base `1.0.0`, followed by the full SONiC source commit under the registry
convention.

The declared Python 3.13 preparation tool runs the production `setup.py build_py`
in an isolated directory with the declared README, raw models and templates.
The production setup checks its model manifest and renders the `py` and `cvl`
variants. The public tree contains the `py` variant used by the model wheel and
Common's generator. This preserves Common's existing preparation behavior.
Python dependencies retain Jinja2 3.1.6, MarkupSafe 3.0.3, pytest-runner 6.0.1,
setuptools 80.9.0 and wheel 0.45.1 with their locked distribution hashes.
The preparation action uses offline installer settings and requests network
blocking; dependency downloads happen during Bazel resolution.

## Public interface

```starlark
bazel_dep(
    name = "sonic-yang-models",
    version = "1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d",
    repo_name = "sonic_yang_models",
)
```

- `@sonic_yang_models//:yang_models`: one directory artifact containing the
  prepared YANG files. Schema generators consume this declared input.
- `@sonic_yang_models//:yang_models_pkg`: a runtime tar installing those files
  under `/usr/local/yang-models`.
- `@sonic_yang_models//:yang_models_package_test`: checks every installed path
  and byte against the prepared tree, with a nonempty YANG-only payload.

Packaging uses repository-relative paths, so the tar layout remains the same
when this module is an external dependency. The model tree is architecture
independent; CI validates preparation and packaging on native AMD64 and ARM64
Debian Trixie with Bazel 8.5.1 and Python 3.13. Its external consumer requests
infrastructure `0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc` for platform labels.

Common retains its own `gen_cfg_schema.py`, generated-header action and consumer
integration tests. This module owns the shared preparation and model runtime
package. It does not add a wheel or Debian package, the `cvl` payload, debug
symbols, or full SONiC image validation.
