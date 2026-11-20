# Build DASH with Bazel

Use Bazel 8.5.1 and the Trixie toolchain. The default platform is AMD64.
On an ARM64 build host, pass both
`--platforms=@sonic_build_infra//platforms:aarch64_trixie` and
`--host_platform=@sonic_build_infra//platforms:aarch64_trixie`.

```sh
bazel build //:sdk //:runtime //:runtime.debug_symbols //:runtime_packages.json
bazel test //bazel:runtime_test
```

| Target | Output |
| --- | --- |
| `//:sdk` | Generated DASH and SAI API headers and the `libsai.so` link interface. |
| `//:runtime` | The two shared libraries under `/usr/lib/<triplet>`, the four BMv2 pipeline files under `/etc/dash`, and license files. |
| `//:runtime.debug_symbols` | Detached symbols for the libraries in the runtime TAR. |
| `//:runtime_packages.json` | Package identity from the DASH Debian control file and dependency metadata derived from the ELF payload. |

The build runs the pinned P4C compiler, the DASH Python generator, and the
SAI Doxygen and Perl metadata generators as separate actions. The DASH
generation action reads the fixed SAI gitlink's headers and writes extended
headers as declared outputs. The metadata action reads those outputs
alongside the unmodified SAI headers. Bazel compiles the three metadata
translation units once per build configuration and links them into both
shared libraries.

The C++ SDK uses the same PI, gRPC, protobuf and Abseil libraries as the
component build. Build tools and C++ dependencies resolve through the declared
toolchain and the shared APT lock. The Python generator uses
`requirements_lock.txt`. The generated `MODULE.bazel.lock` is retained with
the CI evidence.

The runtime test uses the installed libraries and the matching loader from
the declared Debian packages. It checks SDK calls, standalone library loading,
the generated pipeline, and detached symbols with `readelf`, `objcopy` and GDB.
Native CI runs the build and test on AMD64 and ARM64 and records both TARs,
package metadata, toolchain resolution, and test logs.
