# Common runtime data for direct OCI consumption

Registers [Common #34](https://github.com/securely1g/sonic-swss-common/pull/34)
at source commit `9c8c0645b7a30273c3637146eac840cad377b6ff`.
[Buildimage #13](https://github.com/securely1g/sonic-buildimage/pull/13) will consume
`@sonic_swss_common//dist:libswsscommon_pkg` to install these producer-owned files
without correcting their metadata in the image. The consumer update is separate.

| Input or action | Before | After |
| --- | --- | --- |
| Redis Lua runtime files | Mode `0755` | Mode `0644`, root ownership and fixed timestamps. |
| Database configuration | Raw `var/run/redis/sonic-db/database_config.json` | Canonical `run/redis/sonic-db/database_config.json`, mode `0644`, root ownership. The base image preserves `/var/run` access. |

The source package test now checks raw archive metadata and legacy-path access.
The registration carries forward all native AMD64/ARM64 C++, Python, Go, Rust,
runtime/debug and timestamp checks from published `0.0.6-be3495e6958310cb3dd02d6a290a6564efd9aa95`.
Its only patch, `0001-module-version.patch`, updates the source module version
`0.0.6` to this exact registry version. Published entries remain unchanged.

This is an unpublished candidate while Common #34 remains open. After that
source merges, refresh the candidate to the maintained-branch commit before
marking its registry PR Ready. No registry endpoint changes are required.
