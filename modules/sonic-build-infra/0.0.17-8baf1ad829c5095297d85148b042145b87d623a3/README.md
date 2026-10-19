# Use native Bazel shared libraries in C++, Go and Rust

This entry registers `sonic-build-infra@0.0.17-8baf1ad829c5095297d85148b042145b87d623a3`
from [build-infra #51](https://github.com/securely1g/sonic-build-infra/pull/51).
For example, SWSS Common builds `libswsscommon.so.0` once with
`cc_shared_library`. The `shared_library_cc_info` adapter passes its library
paths and runtime files to the C++, Go and Rust rules that consume it. Other
native shared libraries can depend on the same producer directly.

The source uses the linker's default RUNPATH behavior. It selects
`rules_distroless@0.9.4.sonic.6` from
[registry #82](https://github.com/securely1g/sonic-bazel-registry/pull/82), whose
library rules advertise their C++ metadata so Bazel can retain the imported
libraries' runtime paths. Downloaded Debian libraries also need their own
runtime dependencies available. [Common #27](https://github.com/securely1g/sonic-swss-common/pull/27)
installs those dependencies in its test container.

Native AMD64 and ARM64 CI checks an executable that loads a middle library
backed by a leaf library. The ELF checks require RUNPATH, reject RPATH, and
verify that only the middle library is a direct dependency of the executable.
The 17 build targets and 12 tests retain compiler, build-tool, runtime-tar and
matching debug-symbol coverage. They do not generate DEB packages.

This registration uses the merged `master` revision from #51 and targets registry
`main`, where #82 is already available. It replaces the earlier unmerged source
candidate; existing versions on registry main remain unchanged.
