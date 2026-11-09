# DBSyncd

The `sonic-dbsyncd` module exposes the source owner's Python libraries, the
`sonic_d-2.0.0-py3-none-any.whl` wheel, and an installed runtime TAR for native
AMD64 Debian Trixie with Python 3.13.

| Target | Output |
| --- | --- |
| `@sonic-dbsyncd//:lldp_syncd` | LLDP library depending on SWSS Common's public native Python binding |
| `@sonic-dbsyncd//:sonic_syncd` | Reusable synchronization daemon library |
| `@sonic-dbsyncd//:sonic_dbsyncd_wheel` | Owner-only Python wheel |
| `@sonic-dbsyncd//:sonic_dbsyncd_runtime` | Installed wheel under `/usr/local/lib/python3.13/dist-packages` |

The application supplies `sonic-py-common` for the installed
`python3 -m lldp_syncd` entrypoint. The producer does not depend on buildimage or
copy another owner's Python or Rust sources. This pure Python package has no
debug ELF archive. None of these targets produces a Debian package.

The registry source pin is the full source commit; its only patch changes the
Bazel module version to match that pin. The wheel retains the legacy package
version `2.0.0`. The upstream wheel rule cannot express the legacy Maintainer
fields; the source keeps `setup.py` unchanged and records this metadata gap.

Registry CI builds all four public targets in a fresh consumer and runs:

- Archive checks against the fetched source, wheel RECORD hashes, exact wheel
  bytes in the runtime TAR, root ownership, file modes, and zero timestamps.
- Imports of the stdlib-only `sonic_syncd` modules from an extracted runtime TAR
  in an isolated Python process. Installed LLDP imports with their dependency
  closure are covered by the source PR.
- Public LLDP imports with the real source-built Common binding, LLDP time
  parsing, and one real synchronization thread.

The source PR additionally runs all 14 original tests, installed wheel/CLI
dispatch checks, a private Redis update/delete test, and source edit/restore.
The real `lldpctl` process and complete Docker integration are tracked by
[buildimage issue #121](https://github.com/securely1g/sonic-buildimage/issues/121).

The source is the landed [DBSyncd #1](https://github.com/securely1g/sonic-dbsyncd/pull/1)
commit `8a3830704d3f6067823f7c10b3b31913965add81`. Its `tar.bzl@0.10.5.sonic.1` and
`rules_distroless@0.9.4.sonic.15` dependencies are available on the maintained
registry `main`. Normal consumers use that registry endpoint.
