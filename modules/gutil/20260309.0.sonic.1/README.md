# gutil 20260309.0.sonic.1

This entry carries Google's gutil `20260309.0` release with the Bazel Central
Registry's `20260309.0.bcr.1` fix and declares the C++ standard that gutil's
sources need.

gutil's public `gutil/status.h` defines a C++20 concept, so every file that
includes it must compile as C++20. The Bazel Central Registry leaves the
standard to the consumer, and its own presubmit passes `--cxxopt=-std=c++20`.
SONiC modules build without consumer compiler flags, so the C++ targets here
set `-std=c++20` in their own `copts`, as other SONiC modules do with their
standard.

Consumers: `p4_constraints` and `sonic-pins` (P4RT).

Registry CI builds the libraries and the `cc_embed_data` generator and runs the
unit tests with SONiC's Debian Trixie GCC toolchain on native AMD64 and ARM64.
`test_artifact_writer_test` is not run because it needs gutil's development-only
`google_benchmark` dependency, which the Bazel Central Registry excludes too.
