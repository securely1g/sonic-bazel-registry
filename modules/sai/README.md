# SAI

`1.18.0-sonic.1` publishes the Open Compute Project SAI API headers and metadata
generator used by sonic-sairedis, with native AMD64 and ARM64 execution tools.
The exact source and generator provenance are in
[`1.18.0-sonic.1/README.md`](1.18.0-sonic.1/README.md).

```starlark
bazel_dep(name = "sai", version = "1.18.0-sonic.1", repo_name = "sai_source")
```

Consumers select this registry and the Bazel Central Registry. They retain their
own library boundaries, ABI versions, packages, device backends and API entry
stubs. No SAI implementation or vendor SDK is supplied by this module.
