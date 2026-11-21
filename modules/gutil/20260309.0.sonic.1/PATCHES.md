# Patches

- `0001-fix-return-if-error.patch`: the Bazel Central Registry's
  `fix_return_if_error.patch` from gutil `20260309.0.bcr.1`, unchanged. It gives
  the `RETURN_IF_ERROR` loop variable a unique name so it no longer shadows a
  caller's `status`.
- `0002-module-version.patch`: sets the module version to `20260309.0.sonic.1`.
- `0003-declare-cxx20.patch`: adds `copts = ["-std=c++20"]` to the 19 C++
  targets that have sources, so the sources compile as C++20 without consumer
  flags.

None of these patches has been sent to gutil.
