# Default timestamps in tar.bzl

`0.10.5-sonic.1` applies a small timestamp-default patch and its regression
suite to the verified upstream **0.10.5 release archive**. Bazel Central
Registry already supplies unpatched 0.10.5; this explicitly requested local
patch keeps the normal `tar()` / `tar_rule()` APIs and `bsdtar` executable.
It does not add a SONiC tar wrapper.

```starlark
load("@tar.bzl//tar:tar.bzl", "tar")

tar(
    name = "runtime",
    srcs = [":program"],
    mtree = ["usr/bin/program type=file uid=0 gid=0 mode=0755 content=$(location :program)"],
    default_mtime = "1672560000",
)
```

The new optional `default_mtime` attribute defaults to empty, preserving
existing behavior. With an integer Unix timestamp, tar.bzl uses its declared
execution-platform gawk dependency to add an mtree `/set time` fallback.
Explicit entry timestamps and inherited `/set time` values, including zero,
remain authoritative. `/unset time` or `/unset all` restores the fallback.
Both inline and generated manifest files work; other metadata, escaped paths,
continuations and directory navigation stay intact. Existing automatically
generated timestamps are unchanged. Symlinks needing zero use explicit
`time=0`, rather than a special rule in the generic default.

Generic regression tests are part of the tar.bzl patch. Native AMD64 and ARM64
presubmits test real archive bytes using identical input content with different
filesystem mtimes, with an unchanged opt-out negative control. They also cover
inline and generated manifests, explicit and inherited times, `/unset`,
continuations, LF/CRLF manifests, escaped spaces, nested directories, symlinks, owners, modes,
content and unused-input pruning. Invalid integer attributes fail analysis, including whitespace, directives,
leading plus signs and fractional values. Existing manifest times retain their
original mtree syntax, including nanoseconds.
The test checker uses Python 3 supplied by the native CI image; packaging uses
declared gawk and bsdtar tools. Selected targets generate only tar archives.

Consumers are [build-infra #21](https://github.com/securely1g/sonic-build-infra/pull/21)
(`sonic_deploy_tar` runtime archives) and
[SWSS-common #16](https://github.com/securely1g/sonic-swss-common/pull/16)
(the CLI tar and library runtime package). Their package-specific regression
tests remain with those repositories; [registry #33](https://github.com/securely1g/sonic-bazel-registry/pull/33)
publishes the updated build-infra source.

Because `0.10.5-sonic.1` sorts below unpatched `0.10.5`, consuming root modules
must use a `single_version_override` for this version if their graph requests
unpatched 0.10.5. A dependency's own override does not propagate to its users.
Verify the generated lock and fetched module before claiming patch adoption.
