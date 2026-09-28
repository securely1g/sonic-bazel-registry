# sonic-build-infra 0.0.4-7ce718859ccf79fdafbf5cb5abd32bcca164f126

This entry registers source commit
[`7ce718859ccf79fdafbf5cb5abd32bcca164f126`](https://github.com/securely1g/sonic-build-infra/commit/7ce718859ccf79fdafbf5cb5abd32bcca164f126).
It adds an optional installed-runtime-path feature to the `0.0.4` source
baseline at `83b4e9d963f7f268d06983a8c954fc5d6d93ce2b`. The compiler, sysroot,
and dependency inputs remain those of that baseline. The registry patch only
sets the module version to the immutable source-commit version.

The GCC toolchain enables `sonic_installed_runtime_paths` by default. It adds
`/lib/<multiarch>` and `/usr/lib/<multiarch>/gconv` to linked ELF runtime search
paths. Private tools that resolve native dependencies from Bazel runfiles can
disable the feature through its exported name:

```starlark
load("@sonic_build_infra//toolchains/gcc:defs.bzl", "SONIC_INSTALLED_RUNTIME_PATHS_FEATURE")

cc_binary(
    name = "private_tool.so",
    features = ["-" + SONIC_INSTALLED_RUNTIME_PATHS_FEATURE],
    linkshared = True,
    # ...
)
```

The example assumes `repo_name = "sonic_build_infra"` in the consumer's
`bazel_dep`. Loading the exported constant makes this source API an explicit
analysis dependency.

Commit suffixes do not sort by Git history. A root that also brings in another
`0.0.4` source commit should select this exact release when it needs the feature:

```starlark
single_version_override(
    module_name = "sonic-build-infra",
    version = "0.0.4-7ce718859ccf79fdafbf5cb5abd32bcca164f126",
)
```

The source owns four link-action tests covering default and disabled behavior
for executables and shared libraries. `presubmit.json` declares native Trixie
AMD64 and ARM64 builds and tests for the registry consumer. Local validation
used Bazel 8.5.1 on native Trixie AMD64; the source's 30 owner tests passed, and
ELF inspection confirmed the two paths occur once by default and are absent
when disabled.
