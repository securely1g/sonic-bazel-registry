# blkinfo 0.2.0 SONiC source installation

The fixed PyPI source archive supplies the original `blkinfo` package and setup metadata. No product Python files are patched. The direct installation uses published sonic-build-infra 0.0.36 and rules_python 1.9.0.sonic.1.

Public targets:

- `@blkinfo//:blkinfo.runtime`: raw TAR installed under `/usr/local/lib/python3.13/dist-packages`.
- `@blkinfo//:blkinfo.runtime_metadata`: Python distribution identity and runtime dependency metadata.
- `@blkinfo//:installed_test`: installation payload, original metadata, RECORD and source-free public import checks.

```sh
bazel build @blkinfo//:blkinfo.runtime @blkinfo//:blkinfo.runtime_metadata
bazel test @blkinfo//:installed_test
```

The test consumes the actual installation TAR in an isolated Python 3.13 process. It checks the documented public class and the original `NoLsblkFound` error when PATH contains no executable. Live block-device enumeration needs the external util-linux `lsblk` command and Linux `/sys` and `/proc`; this registration test does not access host disks. The original source distribution contains no upstream test suite. Initial native CI coverage is AMD64.
