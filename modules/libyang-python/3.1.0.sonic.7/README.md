# libyang-python 3.1.0.sonic.3

This module builds the libyang-Python binding used by SONiC schema generation.
Its public Python import remains `libyang`; the Bazel module is named
`libyang-python` to distinguish it from the native `libyang` module.

Revision 3 adds the original `setup.py` distribution metadata to the runtime
TAR. Installed consumers can discover `libyang` version `3.1.0`, its required
Python version and its CFFI dependency through `importlib.metadata`.

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
    version = "3.1.0.sonic.3",
    repo_name = "libyang_python",
)
```

This revision uses the registered `sonic-build-infra`
`0.0.17-8baf1ad829c5095297d85148b042145b87d623a3` for runtime TARs and
matching debug symbols. Earlier versions remain unchanged.

Public targets:

- `@libyang_python//:libyang`: Python library and its CFFI extension.
- `@libyang_python//:libyang_pkg`: Python sources, type marker and stripped
  `_libyang.so` installed in `/usr/lib/python3/dist-packages`, the upstream
  `libyang-3.1.0.egg-info` distribution metadata, and the license.
- `@libyang_python//:libyang_pkg.debug_symbols`: matching native debug symbols
  installed by build ID below `/usr/lib/debug`.
- `@libyang_python//:libyang_package_test`: installed import/schema test and
  distribution metadata check, plus debugger lookup using the runtime and
  debug TARs.
- `@libyang_python//:libyang_runtime_test`: Python consumer and declared-runfiles
  test.
- `@libyang_python//:libyang_upstream_test`: the upstream `unittest` suite from
  the patched source tree with its declared model and data fixtures.

The module supplies a Python 3.13 toolchain and its own CFFI `1.17.1` /
pycparser `2.22` dependency hub. Declared setuptools `80.9.0` runs upstream
`setup.py egg_info` as an execution tool in a private source copy. The action
includes the original setup configuration, manifest, license, Python sources
and CFFI generator inputs. It uses upstream's supported version override and
disables package downloads. It creates metadata only; the existing target
compilation continues to produce `_libyang.so`.

The metadata action declares each output explicitly and rejects a changed
upstream metadata inventory. If a source/setuptools update adds metadata files,
update `_EGG_INFO_NAMES` in `overlay/BUILD.bazel`; that list controls the declared
outputs and installed TAR entries. Refresh `source.json` integrity for changed
overlays. The installed package test compares every generated metadata file
with the runtime TAR and discovers the distribution from the extracted files.

Consumers do not need Common's pip hub or build tools. A consuming `py_binary`
or `py_test` must select `python_version = "3.13"`;
the library inherits its consumer's Python configuration. The upstream CFFI
build sets `py_limited_api=False`, so this target is not an ABI3 extension.

The CFFI source emitter runs as a declared execution tool. Bazel compiles the
emitted C in the binding's configuration with the versioned `@python_3_13//:python_headers` alias for the
target platform and links it to the native `libyang` target. It does not
link another `libpython`. The selected SONiC toolchain does not embed the
installed `/lib/<multiarch>` or `/usr/lib/<multiarch>/gconv` runtime paths.
The extension uses Bazel's declared runtime paths without a feature override.

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

The version's `presubmit.json` uses an independent consumer and native AMD64
and ARM64 Debian Trixie jobs with Bazel 8.5.1. CI runs the runtime and upstream
tests, then extracts the packages to check installed imports, a schema/data
roundtrip, the patched leafref API, and installed distribution name, version,
Python requirement and CFFI dependency marker. It verifies that the extension loads the
extracted native libyang library, not a copy from the Bazel output tree.

Packaging uses `sonic_deploy_tar` with debug compilation enabled. The installed
extension is stripped; the companion archive retains DWARF debug information.
The package test compares build IDs, checks the `.gnu_debuglink` checksum and
asks GDB to find a generated CFFI function's source line. A check before adding
the debug archive proves that the debugger is not finding symbols elsewhere.

This artifact is for CPython 3.13 on native AMD64 and ARM64 Linux. Cross-target
binding use, other Python versions, other operating systems and ARMHF are not
validated. Consumers must also install the CFFI runtime and native
`@libyang//:libyang_pkg`; the native library's debug archive remains owned by
that module. The TAR does not run pip or resolve dependencies at image-build
time. This registration does not produce a wheel or Debian package.
The distribution metadata does not create dpkg records or run package
installation scripts. It retains the existing `_libyang.so` filename.

The first downstream consumer is the source-built config-engine base image in
`securely1g/sonic-buildimage`, which needs the Python binding beside libyang.
Its image integration is separate from this producer change.
