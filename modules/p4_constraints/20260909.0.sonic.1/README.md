# p4_constraints 20260909.0.sonic.1

This entry carries the p4-constraints `20260909.0` release and declares the C++
standard its sources need.

Its sources include gutil's `status.h`, which defines a C++20 concept, so they
must compile as C++20. The Bazel Central Registry leaves the standard to the
consumer, and its own presubmit passes `--cxxopt=-std=c++20`. SONiC modules
build without consumer compiler flags, so the C++ targets here set
`-std=c++20` in their own `copts` and depend on `gutil@20260309.0.sonic.1`,
which does the same.

Consumer: `sonic-pins` (P4RT).

Registry CI builds the libraries and `p4check` and runs the unit and golden
tests with SONiC's Debian Trixie GCC toolchain on native AMD64 and ARM64.
`symbolic_interpreter` and its test are not covered: they need Z3, and SONiC
images do not use them.
