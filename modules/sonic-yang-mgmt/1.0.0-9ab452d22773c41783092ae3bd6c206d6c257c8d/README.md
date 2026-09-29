# sonic-yang-mgmt

This module supplies the three production Python modules used by Common's
configuration-schema generator: `sonic_yang`, `sonic_yang_ext`, and
`sonic_yang_path`. Moving this build interface into the registry lets other
consumers use the same library without duplicating Common's source archive,
Python dependencies, and build overlay.

## Source and version

The source is upstream [`sonic-net/sonic-buildimage` commit
`9ab452d22773c41783092ae3bd6c206d6c257c8d`](https://github.com/sonic-net/sonic-buildimage/commit/9ab452d22773c41783092ae3bd6c206d6c257c8d).
The registry retains the [original pinned source archive](https://github.com/securely1g/sonic-bazel-registry/releases/download/source-sonic-buildimage-9ab452d22773c41783092ae3bd6c206d6c257c8d/sonic-buildimage-9ab452d22773c41783092ae3bd6c206d6c257c8d.tar.gz)
as a release asset so fork synchronization cannot remove its download location.
The retained bytes match the original archive exactly; its SHA-256 remains
`006f73ee4e03bbfb1cf03910ebabdc2c0798f64098b1379777c9f70d5e538555`.
`source.json` selects its `src/sonic-yang-mgmt` directory. The source revision,
module version, integrity value and three production Python files are unchanged;
no source patch is applied.

The source `setup.py` declares version `1.0`. The registry normalizes this to
the three-component base version `1.0.0` and appends the full source commit,
giving `1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d`. This follows the
registry policy for modules published from SONiC source repositories.

## Consumer interface

```starlark
bazel_dep(
    name = "sonic-yang-mgmt",
    version = "1.0.0-9ab452d22773c41783092ae3bd6c206d6c257c8d",
    repo_name = "sonic_yang_mgmt",
)
```

Use `@sonic_yang_mgmt//:sonic_yang_mgmt` in a Python binary's dependencies and
select `python_version = "3.13"`. The module supplies Python 3.13, the
registered `libyang-python` `3.1.0-sonic.1` binding, and an isolated pip hub for
locked `jsonpointer` `2.4`. Consumers do not need Common's pip hub or an archive
override. The binding brings its native libyang and CPU-aware SONiC toolchain.

The public `@sonic_yang_mgmt//:sonic_yang_mgmt_sources` target exports the
same three production Python source files for artifact retention. It does not
package an interpreter or dependencies. The runtime test builds and consumes
the real library in its Python 3.13 configuration; a bare top-level library
build would otherwise inherit the consumer's default Python version.

The public `@sonic_yang_mgmt//:sonic_yang_mgmt_runtime_test` loads models from
`sonic-yang-models` at the same source revision. That normal module dependency
is required by the exported test; it does not add model files to the Python
library's runfiles. Applications choose their model directory explicitly.

This registration covers the library interface already consumed by Common.
It does not package the upstream CLI scripts, wheel, or Debian package. Their
additional setup dependencies are outside these three Python modules' import
closure. Prepared models and their deployment archive belong to
`sonic-yang-models`; Common keeps its own schema generator and output tests.

## Validation

The external-consumer presubmit retains `sonic_yang_mgmt_sources`, and builds
and executes
`sonic_yang_mgmt_runtime_test` with Python 3.13 on native AMD64 and ARM64 Debian
Trixie using Bazel 8.5.1. It loads every model in the declared production
payload, checks compiled ConfigDB table mappings, translates and validates a
real syslog configuration, roundtrips a ConfigDB/schema path through the path
mixin, and rejects an out-of-range port. It needs no external services or
installed `/usr/local/yang-models` tree.

The presubmit selects infrastructure
`0.0.6-553b2f70f9ba77b74befdf77674894166139ddcc` through normal module
resolution, with no source or version override. The registry runner verifies
the fetched module identity and requires the runtime test to execute uncached.
