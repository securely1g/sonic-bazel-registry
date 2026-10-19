# Source-built Protobuf Debian runtime

`@protobuf-legacy//sonic:libprotobuf32t64_deb` packages the existing Bazel-built shared library as `libprotobuf32t64` version `3.21.12+sonic.1`. It is consumed by sonic-dash-api and the Orchagent image.

The data comes from the existing source-built runtime TAR. Original Debian source packaging at `3.21.12-11+deb13u1` supplies the package description, install manifest, copyright and time64 transition metadata. Declared `dh_install`, `dh_makeshlibs` and `dh_installdeb` select the library and generate its original installation metadata. `dpkg-shlibdeps` calculates dependencies from the actual ELF file. No prebuilt Debian library is substituted.

The Debian package version retains SONiC's source-build identity; the source compiler, runtime and debug TARs remain unchanged. `libprotobuf32t64_metadata` exposes this actual data and shlibs mapping for downstream dependency generation. Initial package checks ran on AMD64; registration CI validates both native AMD64 and ARM64.

This draft depends on registry #73 and supplies buildimage #33. Keep it Draft until the source tools land.
