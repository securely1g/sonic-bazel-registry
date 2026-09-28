# libyang-python 3.1.0-sonic.1

This module builds the libyang-Python binding used by SONiC schema generation.
Its public Python import remains `libyang`; the Bazel module is named
`libyang-python` to distinguish it from the native `libyang` module.

## Source contract

The source is CESNET/libyang-python `v3.1.0`, fetched from its tagged GitHub
archive with an integrity hash. The four patches are the production series from
[`securely1g/sonic-buildimage` revision `9ab452d22773c41783092ae3bd6c206d6c257c8d`](https://github.com/securely1g/sonic-buildimage/tree/9ab452d22773c41783092ae3bd6c206d6c257c8d/src/libyang3-py3).
The production Make recipe uses the same release and patch order.

`0001-debian.patch`, `0002-pr134-json-string-datatypes.patch`, and
`0004-pr141-test-crash.patch` preserve the production patch bytes.
`0003-pr132-backlinks.patch` preserves its semantic additions and deletions while
refreshing context after patch 0002 for Bazel's strict patcher. Its header records
the original source URL. The original third patch expected `json_null`
immediately before a closing parenthesis; patch 0002 inserts
`json_string_datatypes` there. The refreshed copy adds that unchanged context
line and updates the hunk coordinates.

The established Common comparison against the production Quilt application
found the same 54 paths and identical source bytes, except for a final newline in
`debian/watch` added by Bazel's native patcher. That Debian metadata file is not
an input to this binding build. This module retains the full series so its source
contract remains the same as production.

The native dependency remains `libyang` `3.12.2.sonic.1`, which builds libyang
3.12.2 with SONiC's validation patch. Its PCRE2 and xxHash implementation
libraries are linked statically into `libyang.so.3`. The binding does not fetch
or compile another native libyang copy.

## Build interface

Consumers can use a repository alias while retaining the module name:

```starlark
bazel_dep(
    name = "libyang-python",
    version = "3.1.0-sonic.1",
    repo_name = "libyang_python",
)
```

This release requires the runtime path feature interface from
`sonic-build-infra` `0.0.4-7ce718859ccf79fdafbf5cb5abd32bcca164f126`.
Bzlmod orders commit version suffixes independently of commit chronology,
so another `0.0.4-<commit>` dependency can select a source revision without that
interface. When combining the current SONiC dependency graph, select the required
source version in the root module with a version-only override:

```starlark
single_version_override(
    module_name = "sonic-build-infra",
    version = "0.0.4-7ce718859ccf79fdafbf5cb5abd32bcca164f126",
)
```

The override selects a registered version; it does not replace or patch its
source. This module contains no override. Loading the feature constant makes a
selected infrastructure source without the interface fail during analysis.

Public targets:

- `@libyang_python//:libyang`: Python library and its CFFI extension.
- `@libyang_python//:libyang_runtime_test`: Python consumer and declared-runfiles
  test.
- `@libyang_python//:libyang_upstream_test`: the upstream `unittest` suite from
  the patched source tree with its declared model and data fixtures.

The module supplies a Python 3.13 toolchain and its own CFFI `1.17.1` /
pycparser `2.22` dependency hub. Consumers do not need Common's pip hub or build
tools. A consuming `py_binary` or `py_test` must select `python_version = "3.13"`;
the library inherits its consumer's Python configuration. The upstream CFFI
build sets `py_limited_api=False`, so this target is not an ABI3 extension.

The CFFI source emitter runs as a declared execution tool. Bazel compiles the
emitted C in the binding's configuration with `current_py_cc_headers` from the
selected interpreter and links it to the native `libyang` target. It does not
link another `libpython`. The selected SONiC toolchain's
`SONIC_INSTALLED_RUNTIME_PATHS_FEATURE` constant names the installed path
feature disabled for this private extension, so its loader uses Bazel's declared
runtime paths. The feature comes from the `sonic-build-infra` source version
declared in `MODULE.bazel`.

When a generator consumes this library through an execution transition, the
binding, interpreter, CFFI backend, and native libyang use the execution
configuration. A normal Python consumer uses the target configuration. The
module does not force all uses onto the execution platform.

## Validation and scope

The runtime test imports `libyang`, `_libyang`, and `_cffi_backend`, verifies
that they and the single loaded `libyang.so.3` resolve to declared runfiles, and
roundtrips a schema and JSON data through the binding. It also calls the patched
leafref-target API. The upstream suite exercises the existing context, schema,
data, extension, diff, XPath, and keyed-list tests, including the backlinks tests
from the production patch series. The runner stages only declared test inputs as
regular files in the test temporary directory so native resolved filenames match
the upstream filepath assertions. The runner preserves their bytes and does not
skip tests. It requires no external services.

Without the version override above, the current graph selects
`sonic-build-infra` `0.0.4-83b4e9d963f7f268d06983a8c954fc5d6d93ce2b` requested
by native libyang. The current registry presubmit runner cannot express the root
version-only override, so this entry has no `presubmit.json`. The standalone
consumer and Common integration use the exact registered version selected by
the override above for validation. Registry CI requires a presubmit file for
new entries, so this version cannot pass its planning check until the runner
supports that version selection.

Local validation covers native AMD64 Linux with Debian Trixie userspace, Bazel
8.5.1, and CPython 3.13. The hosted matrix in
[sonic-swss-common#6](https://github.com/securely1g/sonic-swss-common/pull/6)
exercises this module in native AMD64 and ARM64 YANG builds; its checks report
the current results. The locked CFFI setup resolves a wheel for the native host
CPU. Cross-target binding use, other Python versions, other operating systems,
and ARMHF are not validated.

This module supplies a Bazel Python library for build and runtime consumers. It
does not add a wheel, Debian package, or runtime tar. Native libyang runtime and
debug packages remain owned by the native `libyang` module. Common owns model
preparation, schema generation, and its deployment packages.
