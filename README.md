# SONiC Bazel Registry

This registry publishes versioned Bazel dependencies for SONiC. Scope each
module registration or update PR to one module, including its metadata,
sources, patches, overlays, and validation.

## Module version convention

Use these formats for new module versions:

| Source kind | Format | Example |
| --- | --- | --- |
| Third-party (foreign) package | `x.x.x.sonic.y` | `3.12.2.sonic.1` for libyang based on upstream 3.12.2 |
| SONiC source repository | `x.x.x-<commitid>` | `0.0.4-83b4e9d963f7f268d06983a8c954fc5d6d93ce2b` for sonic-build-infra |

Classify a module by its source project, not its name or the owner of a fork.
A third-party package remains third-party when hosted in a SONiC fork.
Modules published from a SONiC source repository use the source-repository
format even if their names do not start with `sonic-`.

### Third-party packages

- `x.x.x` is the upstream package version. It is not the SONiC release,
  buildimage release, ABI version, or a version invented for the registry.
- `y` is the SONiC patch revision for that upstream version. Start at `1` for
  the first SONiC registry revision and increment it when the downstream
  patch set, Bazel overlays, build configuration, or packaging changes. A
  new upstream version starts a new revision sequence at `1`.
- Use the dotted form exactly: `3.12.2.sonic.1`, then
  `3.12.2.sonic.2`. Do not use `-sonic.y`, `.sonic-patched`, or
  `sonic-buildimage` in a new version name.
- Keep the upstream version tied to the actual source. For a snapshot
  beyond an upstream release, identify that release and represent the
  downstream changes explicitly; do not silently label a different source
  snapshot as the release. Record any upstream version mapping needed for
  packages that do not use three numeric components in the module PR.

The registry suffix does not itself change the library's upstream ABI
version or SONAME.

### SONiC source repositories

- `x.x.x` is the source module's base version.
- `<commitid>` is the full Git commit ID of the source revision being
  packaged. Pin `source.json` to that revision and verify its integrity.
  Do not use the registry repository's commit ID or a branch name here.
- Publish source fixes in the SONiC source repository, then register the
  new source commit. Do not append `.sonic.y` or `-sonic.y` to a commit-based
  version to distinguish different patched contents of the same revision.
- Do not put `sonic-buildimage` in the version name.

## Publishing and migrating versions

The version directory, the entry's `MODULE.bazel`, the module's
`metadata.json`, and the fetched source's patched or overlaid `MODULE.bazel`
must agree. Validate the entry through an external Bazel consumer and
verify its required build, runtime, and package targets.

Keep already published versions available with their original contents,
including hyphenated names such as `0.9.4-sonic.1`. Migrate by publishing
a dotted entry and updating consumers' dependency versions and registry
pins. If the dotted name already exists, reuse it only when it has the
required contents; otherwise increment the patch revision. Do not rename,
rewrite, or delete an existing version directory. Keep each module's
migration in its own PR.

### Check Bazel's selected version

Bazel treats the text after `-` as a prerelease suffix. Using `.sonic.y`
in the release part instead puts the patched version above the matching
unpatched upstream release:

```text
0.9.4-sonic.1 < 0.9.4 < 0.9.4.sonic.1 < 0.9.4.sonic.2 < 0.9.5
```

A dotted patch version outranks its matching upstream release, but higher
upstream releases or patch revisions can still win elsewhere in the graph.
Inspect `bazel mod graph`, align dependent version requests, and use a root
`single_version_override` when the consumer needs to enforce a specific
patched version. Re-run the consumer tests after changing resolution.
Commit suffixes also do not sort by Git commit date; a newer source commit
is not necessarily a higher Bazel version.

See Bazel's [version format and selection rules](https://bazel.build/external/module)
and [root-module version overrides](https://bazel.build/rules/lib/globals/module#single_version_override).
