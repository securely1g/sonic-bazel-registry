# Keep Debian library imports compatible with Bazel 8

`0.9.4.sonic.15` changes generated Debian library imports to load `cc_import`
through the public `@rules_cc//cc:cc_import.bzl` entry point. With Bazel 8.5.1
and `rules_cc@0.2.22`, the private implementation requests
`cc_runtimes_toolchain_type`, which that Bazel version does not provide. The
public entry point selects the compatible implementation.

This version starts from published `0.9.4.sonic.14`, introduced by
[registry #146](https://github.com/securely1g/sonic-bazel-registry/pull/146).
It retains the checksum-pinned upstream 0.9.4 archive, patches `0002`–`0017`,
all overlays and fixtures, seven build targets and all 33 test targets.
`0001` updates only the module version; `0018` changes the import path.
Published versions remain unchanged.

For example, a consumer can link Lua with the package's individual
`liblua5.4_cc` target and receive its declared headers and runtime library
without selecting a library from a package-level provider. The existing
`lua_single_library_test` exercises that contract. The public headers-only
interfaces, declared GNU linker-script inputs and Perl CORE includes from
`.sonic.14` are retained.

## Validation

The independent [integration module](tests/integration/MODULE.bazel) explicitly
selects `rules_cc@0.2.22` with this candidate. On native AMD64 and ARM64, CI
builds all seven inherited outputs and runs all 33 inherited tests uncached,
including real Protobuf/Lua/xtables/libpcap headers, individual Lua linking,
native shared-library RUNPATH behavior, lock imports, original archive identity,
APT installation helpers and OCI account layers. Existing library imports
exercise the public `cc_import` path with the affected Bazel/rules_cc versions.

The recipe downloads and extracts existing checksum-pinned Debian archives.
`apt_install` installs those inputs into a filesystem TAR and receipt; no new
DEB package is produced. Full installed-image validation belongs to consumers.

See [patch provenance and validation](PATCHES.md) for the retained patch chain
and detailed contracts. The locked-import fixture can be regenerated from a
reviewed image lock with:

```sh
entry=modules/rules_distroless/0.9.4.sonic.15
python3 "$entry/tests/integration/tools/select_lock_fixture.py" \
  --input /path/to/sonic-buildimage/dockers/docker-base-trixie/bazel/apt.lock.json \
  --output "$entry/tests/integration/apt.lock.json"
```

The helper selects existing metadata; review package URLs, hashes, versions and
closures before committing a refreshed fixture.
