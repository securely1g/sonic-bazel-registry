# bitarray 2.8.1.sonic.2

SONiC config-engine uses bitarray 2.8.1 on CPython 3.13. The module builds
both C extensions from [upstream source](https://github.com/ilanschnell/bitarray/tree/eb1f7014446ef5ce0afddd86d2e929975ec7b4f9)
using Bazel C actions and the CPython 3.13 headers. The supported wheel is
`bitarray-2.8.1-cp313-cp313-linux_x86_64.whl` for ordinary CPython on
AMD64 Linux with glibc.

Use `@bitarray//:pkg` as a Python dependency and `@bitarray//:whl` as input
to the shared `wheel_layer` rule. Consumers must select Python 3.13.
The wheel includes both extensions, upstream Python and typing files, headers,
pickle fixtures, tests, and the upstream license. The wheel writer emits
Core Metadata 2.4, places the license under `.dist-info/licenses/`, and sets
regular files to 0644, including the loadable shared extensions.

Registry CI exercises the upstream test classes, checks wheel contents and ELF
ABI, and runs the upstream tests a second time from the installed wheel layer.

`@bitarray//:bitarray.runtime` directly installs the same compiled extensions
and package files into `/usr/local/lib/python3.13/dist-packages`. Its default
output is an uncompressed TAR; PythonRuntimeInfo and the
`@bitarray//:bitarray.runtime_metadata` JSON output describe that distribution.
The wheel and TAR share one metadata declaration and both native extension
producers. The direct installation graph does not build or unpack the wheel.
Registry CI retains all three wheel/upstream tests and runs the same complete
upstream suite from the direct installation TAR.
