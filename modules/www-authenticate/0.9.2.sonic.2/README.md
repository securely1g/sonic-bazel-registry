## Dependency refresh for `0.9.2.sonic.2`

This candidate retains the `0.9.2.sonic.1` source and existing patches. Its module dependencies select the newest non-yanked versions published at `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. Versions introduced by this refresh are not dependency targets of the same refresh.

# www-authenticate 0.9.2 SONiC installation

Register the original PyPI source and metadata as a direct Python 3.13 installation. SONiC utilities pins this version in setup.py. Product Python source is unchanged.

- `@www-authenticate//:www-authenticate.runtime`: raw installation TAR.
- `@www-authenticate//:www-authenticate.runtime_metadata`: Python distribution metadata.
- `@www-authenticate//:installed_test`: installed payload, metadata, RECORD and documented parser interfaces.

```sh
bazel build @www-authenticate//:www-authenticate.runtime @www-authenticate//:www-authenticate.runtime_metadata
bazel test @www-authenticate//:installed_test
```

The installation test imports the TAR contents in an isolated Python 3.13 process. Hand-checkable examples cover Basic parameter dictionaries, quoted commas, Negotiate opaque values, parameterless challenges and ordering. They follow the upstream README contract; this test does not claim complete HTTP authentication conformance. The original source archive contains no upstream test suite. Initial native CI coverage is AMD64. Dependencies use published infrastructure .36 and rules_python 1.9.0.sonic.1.
