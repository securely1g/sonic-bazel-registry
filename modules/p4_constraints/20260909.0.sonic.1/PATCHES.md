# Patches

- `0001-module-version.patch`: sets the module version to `20260909.0.sonic.1`.
- `0002-declare-cxx20.patch`: adds `copts = ["-std=c++20"]` to the 23 C++
  targets that have sources and depends on `gutil@20260309.0.sonic.1`, so the
  sources and gutil compile as C++20 without consumer flags.
- `0003-diff-test-shebang.patch`: adds `#!/usr/bin/env bash` to `p4check.bzl`'s
  generated `diff_test` script so the ARM64 cross-test executor (`sonic-arm64`)
  can invoke it instead of failing with `Exec format error`.

None of these patches have been sent to p4-constraints.
