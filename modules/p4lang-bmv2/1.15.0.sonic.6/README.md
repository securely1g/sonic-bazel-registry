## Dependency refresh for `1.15.0.sonic.6`

This candidate retains the `1.15.0.sonic.5` source and existing patches. Its module dependencies select the newest non-yanked versions published at `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. Versions introduced by this refresh are not dependency targets of the same refresh.

# Native BMv2 for SONiC

Builds the fixed BMv2 1.15.0-9 input from `src/p4lang/Makefile` with native Bazel C/C++ rules. The ordered source preparation applies Debian’s series and all three SONiC patches. PI is consumed through the native `p4lang-pi@0.1.3.sonic.6` public libraries. System libraries and execution tools share the existing production APT lock.

The original fixed PDFixed, Thrift, nanomsg, PI and gRPC configuration is retained. Thrift and protoc actions declare their source/import inputs and generated C++/Python outputs. Configuration detection belongs to migration evidence; normal builds use explicit configuration and template expansion.

Public interfaces: `p4lang-bmv2.runtime`, `p4lang-bmv2.runtime.debug_symbols`, `development`, `sdk`, `p4lang-bmv2.runtime_metadata`, `sdk_consumer`, `check_programs`, `upstream_tests`, and `package_test`. The existing `runtime`, `runtime.debug_symbols` and `runtime_packages.json` names remain compatible for current consumers. Runtime and development TARs together preserve the source package’s installation contract. No Debian package is generated.

The original 54 default Automake test entries are represented by `upstream_tests`. Each test also has a same-named public suite, and presubmit lists the individual entries so the registry collector checks every executed test summary. `check_programs` also builds the upstream check-only and non-installed programs. Stress tests retain their original disabled selection. The two gRPC checks use the shared native target-runtime rules with declared APT and PI/BMv2 TAR payloads; their upstream source and assertions are preserved. `package_test` exercises installed programs, the public SDK, generated Thrift Python interfaces, library SONAMEs and matching DWARF/build-id/debuglink data. Privileged network forwarding is outside this installation check.

The original archive and Debian packaging come from the p4lang OBS project for Debian 11. The checksum-pinned registry release mirror supplies the same two files used in BMv2 .4. Ordered source preparation also retains the OBS origins as fallbacks.

Original source SHA256: `083bb907e45597af8e29ef3b0a92d33d282ba23840ddd5cfb8372d2f030ab415`. Debian archive SHA256: `30941da6dde4cbbefaa9a12dfffa260115b3b63c6d56b3112b3baee953636179`. The original archive retains revision `68f4a978f465fd76e98fcdecb762981843fb7310`; its version suffix is preserved. The registry archive supplies the module entry, while the shared ordered source repository merges Debian metadata and patches for compilation. Identical original-archive downloads share Bazel’s checksum cache; the two extraction stages remain separate.

Installed static archives use the target-aware `strip_static_archive` rule from sonic-build-infra .38. Native and cross builds select binutils for the target object architecture while running on the execution platform.

The packet-redirect test uses a private short IPC directory per process. Parallel instances previously bound the same two absolute paths under /tmp; the packet assertions and test selection are unchanged.

The eleven C++ tests that load libpcap and the five CLI tests that start simple_switch use the declared Trixie runtime, including libpcap’s libdbus dependency. Each CLI test waits for its own Thrift endpoint and stops the complete switch process group when it finishes.
